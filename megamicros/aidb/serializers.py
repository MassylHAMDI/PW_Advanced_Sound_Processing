# megamicros_aidb/apps/aidb/core/serializers.py
#
# Copyright (c) 2023 Sorbonne Université
# Author: bruno.gas@sorbonne-universite.fr
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""
Megamicros AIDB serializers

MegaMicros documentation is available on https://readthedoc.biimea.io
"""



from array import array
from os import listdir, path as ospath
import io
import wave
import ffmpeg
import uuid
import json
import ast
import numpy as np
from contextlib import nullcontext
from datetime import datetime, timedelta
from pytz import timezone
from pathlib import Path
import h5py
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse
from django.db import models
from rest_framework import serializers
from rest_framework.response import Response
from .models import Config, Domain, Campaign, Device, Directory, Tagcat, Tag, SourceFile, Context, FileContexting, Label, FileLabeling, Dataset
from .sp import compute_q50_from_file, compute_energy_from_file, compute_energy_from_wavfile, extract_range_from_wavfile, compute_energy_from_muh5file, extract_range_from_muh5file, genwav_from_range_wavfile, genwav_from_range_muh5file
from .sp import save_context_on_muh5_file, update_context_on_muh5_file, save_label_on_muh5_file, update_label_on_muh5_file, save_dataset_on_muh5_file, remove_dataset_muh5_file
from megamicros.log import log

"""
Django Rest Framework ManyToMany through, see: https://bitbucket.org/snippets/adautoserpa/MeLa/django-rest-framework-manytomany-through
"""


"""
Some additional validators for serializers
"""
class PathValidator:
    def __init__( self, max_length=256, fieldname='path' ):
        self.fieldname = fieldname
        self.max_length = max_length

    def __call__( self, fields ):
        if len( fields[self.fieldname] ) > self.max_length:
            message = f"Path {fields[self.fieldname]} is too long. Please check"
            raise serializers.ValidationError( message )

        if ospath.exists( fields[self.fieldname] ) == False:
            message = f"Path <{fields[self.fieldname]}> does not exist. Please check path existance"
            raise serializers.ValidationError( message )

"""
Base serializer classes
"""
class ConfigSerializer( serializers.ModelSerializer ):
    uddate = serializers.DateTimeField( read_only=True )

    class Meta:
        model = Config
        fields = ['id', 'url', 'host', 'dataset_path', 'active', 'comment', 'crdate', 'uddate']
        validators = [PathValidator( fieldname='dataset_path' )]
    
    def create(self, validated_data):
        if validated_data['active'] == True:
            """
            Deactivate any other config
            """
            Config.objects.filter( active=True ).update( active=False )

        log.info( f" .Successfully created new config" )
        return Config.objects.create( **validated_data )

    def update( self, instance: Config, validated_data ):

        instance.host = validated_data.get( 'host', instance.host )
        instance.dataset_path = validated_data.get( 'dataset_path', instance.dataset_path )
        instance.active = validated_data.get( 'active', instance.active )
        instance.comment = validated_data.get( 'comment', instance.comment )
        instance.uddate = datetime.now()

        if instance.active == True:
            """
            Deactivate any other config
            """
            Config.objects.filter( active=True ).update( active=False )

        instance.save()
        log.info( f" .Successfully updated config" )

        return instance


class TagcatSerializer( serializers.ModelSerializer ):
    tags = serializers.HyperlinkedRelatedField( many=True, read_only=True, view_name='tag-detail' )

    class Meta:
        model = Tagcat
        fields = ['id', 'url', 'name', 'comment', 'crdate', 'tags']

class TagSerializer( serializers.ModelSerializer ):
    contexts = serializers.HyperlinkedRelatedField( many=True, read_only=True, view_name='context-detail' )
    labels = serializers.HyperlinkedRelatedField( many=True, read_only=True, view_name='label-detail' )
    filelabelings = serializers.HyperlinkedRelatedField( many=True, read_only=True, view_name='filelabeling-detail' )

    class Meta:
        model = Tag
        fields = ['id', 'url', 'name', 'tagcat', 'comment', 'contexts', 'labels', 'filelabelings', 'crdate']

class DomainSerializer( serializers.HyperlinkedModelSerializer ):
    campaigns = serializers.HyperlinkedRelatedField( many=True, read_only=True, view_name='campaign-detail' )
    contexts = serializers.HyperlinkedRelatedField( many=True, read_only=True, view_name='context-detail' )
    labels = serializers.HyperlinkedRelatedField( many=True, read_only=True, view_name='label-detail' )
    datasets = serializers.HyperlinkedRelatedField( many=True, read_only=True, view_name='dataset-detail' )

    class Meta:
        model = Domain
        fields = ['id', 'url', 'name', 'comment', 'info', 'crdate', 'campaigns', 'contexts', 'labels', 'datasets']

class CampaignSerializer( serializers.HyperlinkedModelSerializer ):
    directories = serializers.HyperlinkedRelatedField( many=True, read_only=True, view_name='directory-detail' )

    class Meta:
        model = Campaign
        fields = ['id', 'url', 'domain', 'name', 'date', 'comment', 'info', 'crdate', 'directories']

class DeviceSerializer( serializers.HyperlinkedModelSerializer ):
    directories = serializers.HyperlinkedRelatedField( many=True, read_only=True, view_name='directory-detail' )

    class Meta:
        model = Device
        fields = ['id', 'url', 'name', 'type', 'identifier', 'comment', 'info', 'crdate', 'directories']

class DirectorySerializer( serializers.HyperlinkedModelSerializer ):
    class Meta:
        model = Directory
        fields = ['id', 'url', 'name', 'path', 'campaign', 'device', 'comment', 'info', 'crdate']
        validators = [PathValidator()]

class DirectoryFileSerializer( serializers.HyperlinkedModelSerializer ):
    files = serializers.HyperlinkedRelatedField( many=True, read_only=True, view_name='sourcefile-detail' )

    class Meta:
        model = Directory
        fields = ['id', 'url', 'name', 'path', 'campaign', 'device', 'files', 'comment', 'info', 'crdate']
        validators = [PathValidator()]

class ContextSerializer( serializers.HyperlinkedModelSerializer ):
    class Meta:
        model = Context
        fields = ['id', 'url', 'parent', 'children', 'domain', 'name', 'code', 'type', 'comment', 'info', 'tags', 'crdate']

    def get_fields( self ):
        """ because of self-reference we have to define ourself the children field """ 
        fields = super( ContextSerializer, self).get_fields()
        fields['children'] = ContextSerializer( many=True, read_only=True )
        return fields

class LabelSerializer( serializers.HyperlinkedModelSerializer ):
    class Meta:
        model = Label
        fields = ['id', 'url', 'parent', 'children', 'domain', 'name', 'code', 'comment', 'info', 'tags', 'crdate']

    def get_fields( self ):
        """ because of self-reference we have to define ourself the children field """ 
        fields = super( LabelSerializer, self).get_fields()
        fields['children'] = LabelSerializer( many=True, read_only=True )
        return fields

class SourceFileSerializer( serializers.HyperlinkedModelSerializer ):
    contexts = ContextSerializer( many=True, read_only=True,  )
    labels = LabelSerializer( many=True, read_only=True,  )
    
    class Meta:
        model = SourceFile
        fields = ['id', 'url', 'filename', 'type', 'datetime', 'duration', 'directory', 'size', 'integrity', 'contexts', 'labels', 'tags', 'comment', 'info', 'crdate']

class FileContextingSerializer( serializers.HyperlinkedModelSerializer):
    code = serializers.HiddenField( default='' )
    sourcefile_id = serializers.ReadOnlyField( source='sourcefile.id' )
    sourcefile_filename = serializers.ReadOnlyField( source='sourcefile.filename' )
    context_id = serializers.ReadOnlyField( source='context.id' )
    context_name = serializers.ReadOnlyField( source='context.name' )
    context_code = serializers.ReadOnlyField( source='context.code' )
    context_type = serializers.ReadOnlyField( source='context.type' )
    context_start = serializers.ReadOnlyField( source='context.datetime_start' )
    context_end = serializers.ReadOnlyField( source='context.datetime_end' )

    class Meta:
        model = FileContexting
        fields = ['id', 'url', 'sourcefile', 'context', 'datetime_start', 'datetime_end', 'code', 'comment', 'info', 'sourcefile_id', 'sourcefile_filename', 'context_id', 'context_name', 'context_code', 'context_type', 'context_start', 'context_end']

    """
    validation
    """
    def validate( self, data ):
        if data['datetime_start'] >= data['datetime_end']:
            raise serializers.ValidationError("Context should start before finishing")
        
        """
        Generate the uniqueless code
        """
        if data['code'] == '':
            """
            Generate an uuid code only if we are in create mode
            """
            data['code'] = str( uuid.uuid1() )

        return data


    def create(self, validated_data):

        """
        Save context on file
        """
        sourcefile: SourceFile = validated_data['sourcefile']
        directory: Directory = sourcefile.directory
        context: Context = validated_data['context']
        segment_code = uuid.UUID( validated_data['code'] ).fields
        log.info( f' .Generated segment code is {segment_code}' )

        """ We abandon storing labels and contexts on original source file """
        #save_context_on_muh5_file( 
        #    directory.path + '/' + sourcefile.filename, 
        #    context.code, 
        #    segment_code, 
        #    validated_data['datetime_start'], 
        #    validated_data['datetime_end']
        #)

        return FileContexting.objects.create( **validated_data )


    def update(self, instance: FileContexting, validated_data):
        """
        Can update following fields (but not sourcefile, nor contexting code)
        """
        instance.context = validated_data.get( 'context', instance.context )
        instance.comment = validated_data.get( 'comment', instance.comment )
        instance.info = validated_data.get( 'info', instance.info )
        instance.datetime_start = validated_data.get( 'datetime_start', instance.datetime_start )
        instance.datetime_end = validated_data.get( 'datetime_end', instance.datetime_end )

        """ We renounce to update origin files when labeling """
        #update_context_on_muh5_file( 
        #    instance.sourcefile.directory.path + '/' + instance.sourcefile.filename,
        #    instance.context.code,
        #    list( uuid.UUID( instance.code ).fields ),
        #    instance.datetime_start,
        #    instance.datetime_end
        #)

        instance.save()
        log.info( f" .Successfully updated segment {instance.code}" )

        return instance


class FileLabelingSerializer( serializers.HyperlinkedModelSerializer  ):
    code = serializers.HiddenField( default='' )
    sourcefile_id = serializers.ReadOnlyField( source='sourcefile.id' )
    sourcefile_filename = serializers.ReadOnlyField( source='sourcefile.filename' )
    label_id = serializers.ReadOnlyField( source='label.id' )
    label_name = serializers.ReadOnlyField( source='label.name' )
    label_code = serializers.ReadOnlyField( source='label.code' )

    class Meta:
        model = FileLabeling
        fields = ['id', 'url', 'sourcefile', 'label', 'contexts', 'tags', 'datetime_start', 'datetime_end', 'code', 'comment', 'info', 'crdate', 'sourcefile_id', 'sourcefile_filename', 'label_id', 'label_name', 'label_code']

    """
    validation
    """
    def validate( self, data ):
        """ 
        Validate data if they are provided. 
        Note that with the [PATCH] request, some data may not be provided 
        """
        log.info( ' .Validating file labelling with data: ' + str( data ) )
        if 'datetime_start' in data and 'datetime_end' in data:
            if data['datetime_start'] >= data['datetime_end']:
                log.info( ' .Label should start before finishing' )
                raise serializers.ValidationError("Label should start before finishing")

        """
        Generate the uniqueless code
        """
        if 'code' in data and data['code'] == '':
            """
            Generate an uuid code only if we are in create mode, that is if code is submitted and empty
            """
            data['code'] = str( uuid.uuid1() )

        return data



"""
Processing seralizer classes
"""
class SourceDirectoryCheckSerializer:    
    """
    Check directory existance and return content info 
    """
    def __init__( self, dir: Directory, context=None ):
        try:
            h5 = []
            muh5 = []
            wav = []
            mp4 = []
            other = []
            content = listdir( dir.path )
            for filename in content:
                ext = Path( filename ).suffix
                if ext == '.h5':
                    """
                    check for muh5 file
                    """
                    try:
                        with h5py.File( dir.path + '/' + filename, 'r' ) as muh5_file:
                            if not muh5_file['muh5']:
                                h5.append( filename)
                            else:
                                muh5.append( filename)
                    except Exception as e:
                        continue

                elif ext == '.wav':
                    wav.append( filename)
                elif ext == '.mp4':
                    mp4.append( filename)
                else:
                    other.append( filename )

            self.data = { 
                'status': 'ok',
                'path': dir.path,
                #'device': dir.device,
                'number': {
                    'h5': len( h5 ), 'muh5': len( muh5 ), 'wav': len( wav ), 'mp4': len( mp4 ), 'other': len( other ),
                    'total': len( h5 ) + len( muh5 ) + len( wav ) + len( mp4 ) + len( other )
                },
                'content': {
                    'h5' : h5, 'muh5': muh5, 'wav': wav, 'mp4': mp4, 'other': other
                }
            }

        except Exception as e:
            self.data = { 'status': 'error', 'message': str( e ) }


class SourceDirectoryReviseSerializer:
    """
    Update directory by recording content in database.
    Records file name are supposed following the 'xxx-YYYmmdd-hhmmss.ext' format with local time set to Europe/Paris:
        datetime = pytz.timezone( 'Europe/Paris' ).localize( datetime.strptime(s, '%Y%m%d %H%M%S') )
    More general way could be to considere filenames coded as UTC. We would have then to replace UTC time zone by the local time zone:
        from datetime import datetime, timezone
        datetime_utc = datetime.strptime(s, '%Y%m%d %H%M%S').replace( tzinfo=timezone.utc )
        datetime = datetime_utc.astimezone( pytz.timezone( 'Europe/Paris' ) )
    """
    ERROR_ALREADY_EXIST = 1
    ERROR_NOT_MUH5 = 2
    ERROR_NOT_H5 = 3
    ERROR_OPEN = 4
    ERROR_MODEL_CREATE = 5
    ERROR_NOT_WAV = 6
    ERROR_NOT_MP4 = 7
    ERROR_NOT_IMPLEMENTED = 8

    def __init__( self, dir: Directory, context=None ):
        try:
            response = []
            files = listdir( dir.path )
            for file in files:
                filename = dir.path + '/' + file
                if SourceFile.objects.filter( directory=dir, filename=file ).exists():
                    """
                    file already in database
                    """
                    response.append( {'filename': file, 'status': 'error', 'code': self.ERROR_ALREADY_EXIST, 'message': f"file {file} already exists in db"} )
                else:
                    try:
                        ext = Path( file ).suffix
                        if ext == '.h5':
                            with h5py.File( filename, 'r' ) as h5_file:
                                if not h5_file['muh5']:
                                    """
                                    this is an ordinary H5 file
                                    """
                                    dt = ospath.splitext( file )[0].split( '-' )
                                    if len( dt ) != 3:
                                        """
                                        Seems that filename has not the type-date-time.h5 form -> set initial unix time
                                        Beware that using info['ctime'] may lead to errors since this date can be the last copy date for example
                                        """
                                        dt = datetime.fromtimestamp( 0 )
                                    else:                            
                                        dt = timezone( 'UTC' ).localize( datetime.strptime( dt[1] + ' ' + dt[2], '%Y%m%d %H%M%S') )
                                        dt = dt + timedelta( milliseconds=0 )

                                    """
                                    create and save File object in database
                                    """
                                    try:
                                        h5_object = SourceFile(
                                            filename = file,
                                            type = SourceFile.H5,
                                            datetime = dt,
                                            duration = int( 0 ),                                # unknown duration
                                            size = 0,                                          # unknown size
                                            integrity = True,
                                            directory = dir,
                                            info = {
                                                'ctime': datetime.fromtimestamp( ospath.getctime( filename ) ).strftime( '%Y-%m-%d %H:%M:%S.%f' ),
                                                'mtime': datetime.fromtimestamp( ospath.getmtime( filename) ).strftime( '%Y-%m-%d %H:%M:%S.%f' ),
                                                'size': ospath.getsize( filename )
                                            }                           
                                        )
                                        h5_object.save()

                                    except Exception as e:
                                        response.append( {'filename': file, 'status': 'error', 'code': self.ERROR_MODEL_CREATE, 'message': f"Unable to create db model from file {file}: {e}"} )
                                        continue

                                    response.append( {'filename': file, 'status': 'ok'} )
                                
                                else:
                                    """
                                    this is a MUH5 file
                                    """         
                                    group = h5_file['muh5']
                                    info = dict( zip( group.attrs.keys(), group.attrs.values() ) )
                                    try:
                                        """
                                        get datetime from file internal parameter 'date'
                                        """
                                        try:
                                            dt = timezone( 'UTC' ).localize( datetime.strptime( info['date'], '%Y-%m-%d %H:%M:%S.%f') )        
                                        except Exception as e:
                                            # try to confirm validity without the microseconds field
                                            dt = timezone( 'UTC' ).localize( datetime.strptime( info['date'], '%Y-%m-%d %H:%M:%S') )

                                            # check if there are microseconds in the file timestamp
                                            timestamp = float( info['timestamp'] )
                                            dt_corrected = datetime.fromtimestamp( timestamp )

                                            # fix datetime if possible
                                            if dt_corrected.microsecond != 0:
                                                dt = datetime( dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second, dt_corrected.microsecond )
                                            
                                            # fix date with the good format (whatever the previous fix):
                                            info['date'] = dt.strftime( '%Y-%m-%d %H:%M:%S.%f' )

                                        """
                                        create and save File object in database
                                        """
                                        h5_object = SourceFile( 
                                            filename = file,
                                            type = SourceFile.MUH5,
                                            datetime = dt,
                                            duration = int( info['duration'] ),
                                            size = ospath.getsize( filename ),                            
                                            integrity = True,
                                            directory = dir,
                                            info = {
                                                'ctime': datetime.fromtimestamp( ospath.getctime( filename ) ).strftime( '%Y-%m-%d %H:%M:%S.%f' ),
                                                'mtime': datetime.fromtimestamp( ospath.getmtime( filename ) ).strftime( '%Y-%m-%d %H:%M:%S.%f' ),
                                                'size': ospath.getsize( filename ),
                                                'sampling_frequency': float( info['sampling_frequency'] ),
                                                'timestamp': float( info['timestamp'] ),
                                                'duration': float( info['duration'] ),
                                                'date': info['date'],
                                                'channels_number': int( info['channels_number'] ),          # int64 is not JSON serializable
                                                'analogs_number': int( info['analogs_number'] ),            # idem...
                                                'mems_number': int( info['mems_number'] ),
                                                'dataset_number': int( info['dataset_number'] ),
                                                'dataset_duration': int( info['dataset_duration'] ),
                                                'dataset_length': int( info['dataset_length'] ),
                                                'compression': int( info['compression'] ),                  # bool_ is not JSON serializable
                                                'counter': int( info['counter'] ),                          # bool_ is not JSON serializable
                                                'counter_skip': int( info['counter_skip'] ),                # bool_ is not JSON serializable
                                                'analogs': info['analogs'].tolist(),                        # array is not JSON serializable
                                                'mems': info['mems'].tolist()                               # idem...
                                            }
                                        )
                                        h5_object.save()
                                    except Exception as e:
                                        response.append( {'filename': file, 'status': 'error', 'code': self.ERROR_MODEL_CREATE, 'message': f"Unable to create db model from file {file}: {e}"} )
                                        continue

                                    response.append( {'filename': file, 'status': 'ok'} )                            

                        elif ext == '.wav':
                            with wave.open( filename, 'r' ) as wav_file:
                                """
                                get datetime from filename
                                """
                                dt = ospath.splitext( file )[0].split( '-' )
                                if len( dt ) != 3:
                                    """
                                    Seems that filename has not the type-date-time.wav form -> set initial unix time
                                    Beware that using info['ctime'] may lead to errors since this date may be the last copy date for example
                                    """
                                    dt = datetime.fromtimestamp( 0 )
                                else:                            
                                    dt = timezone( 'UTC' ).localize( datetime.strptime( dt[1] + ' ' + dt[2], '%Y%m%d %H%M%S') )
                                    dt = dt + timedelta( milliseconds=0 )

                                info = {
                                    'ctime': datetime.fromtimestamp( ospath.getctime( filename ) ).strftime( '%Y-%m-%d %H:%M:%S.%f' ),
                                    'mtime': datetime.fromtimestamp( ospath.getmtime( filename) ).strftime( '%Y-%m-%d %H:%M:%S.%f' ),
                                    'size': ospath.getsize( filename ),
                                    'sampling_frequency': float( wav_file.getframerate() ),
                                    'samples_number': wav_file.getnframes(),                                    # samples number
                                    'channels_number': wav_file.getnchannels(),                                 # channels number
                                    'compression': 0 if wav_file.getcomptype() == 'NONE' else 1,                # compressed or not
                                    'compression_type': wav_file.getcomptype(),                                 # compression algo
                                    'compression_name': wav_file.getcompname(),                                 # human readable compression type
                                    'sample_width': wav_file.getsampwidth(),                                    # sample width in bytes
                                    'duration': float( wav_file.getnframes()/float( wav_file.getframerate() ) )
                                }

                                """
                                create and save File object in database
                                """
                                try:
                                    wav_object = SourceFile(
                                        filename = file,
                                        type = SourceFile.WAV,
                                        datetime = dt,
                                        duration = int( info['samples_number']//info['sampling_frequency'] ),           # duration in seconds
                                        size = ospath.getsize( filename ),          
                                        integrity = True,
                                        directory = dir,
                                        info = info                            
                                    )
                                    wav_object.save()
                                except Exception as e:
                                    response.append( {'filename': file, 'status': 'error', 'code': self.ERROR_MODEL_CREATE, 'message': f"Unable to create db model from file {file}: {e}"} )
                                    continue
                                
                                response.append( {'filename': file, 'status': 'ok'} )

                        elif ext == '.mp4':
                            info = ffmpeg.probe( filename, cmd='ffprobe' )

                            dt = ospath.splitext( file )[0].split( '-' )
                            if len( dt ) != 3:
                                """
                                Seems that filename has not the type-date-time.mp4 form -> set initial unix time
                                Beware that using info['ctime'] may lead to errors since this date may be the last copy date for example
                                """
                                dt = datetime.fromtimestamp( 0 )
                            else:
                                #dt = timezone( 'Europe/Paris' ).localize( datetime.strptime( dt[1] + ' ' + dt[2], '%Y%m%d %H%M%S') )                            
                                dt = timezone( 'UTC' ).localize( datetime.strptime( dt[1] + ' ' + dt[2] + '.0', '%Y%m%d %H%M%S.%f') )   
                                dt = dt + timedelta( milliseconds=0 )                         

                            """
                            create and save File object in database
                            """
                            try:
                                mp4_object = SourceFile(
                                    filename = file,
                                    type = SourceFile.MP4,
                                    datetime = dt,
                                    duration = int( float( info['format']['duration'] ) ),                      # duration in seconds
                                    size = ospath.getsize( filename ),
                                    integrity = True,
                                    directory = dir,
                                    info = {
                                        'ctime': datetime.fromtimestamp( ospath.getctime( filename ) ).strftime( '%Y-%m-%d %H:%M:%S.%f' ),
                                        'mtime': datetime.fromtimestamp( ospath.getmtime( filename) ).strftime( '%Y-%m-%d %H:%M:%S.%f' ),
                                        'size': ospath.getsize( filename ),
                                        'frame_rate': info['streams'][0]['r_frame_rate'],
                                        'time_base': info['streams'][0]['time_base'],
                                        'nb_frames': int( info['streams'][0]['nb_frames'] ),
                                        'duration': float( info['format']['duration'] ),
                                        'width': info['streams'][0]['width'],
                                        'height': info['streams'][0]['height'],
                                        'format': info['format']
                                    }                     
                                )
                                mp4_object.save()

                            except Exception as e:
                                response.append( {'filename': file, 'status': 'error', 'code': self.ERROR_MODEL_CREATE, 'message': f"Unable to create db model from file {file}: {e}"} )
                                continue

                            response.append( {'filename': file, 'status': 'ok'} )

                        else:
                            response.append( {'filename': file, 'status': 'error', 'code': self.ERROR_NOT_IMPLEMENTED, 'message': f"Unknown or not implemented file type <{ext}>"} )

                    except Exception as e:
                        response.append( {'filename': file, 'status': 'error', 'code': self.ERROR_OPEN, 'message': f"file {file} opening failed: {e}"} )

            self.data = { 'status': 'ok', 'response': response }

        except Exception as e:
            self.data = { 'status': 'error', 'message': str( e )}



class SourceFileUploadSerializer:
    """
    Check file existance and upload it 
    """

    ERROR_UNCHECKED = 1
    ERROR_SYSTEM = 2

    def __init__( self, file: SourceFile, context=None ):
        if file.integrity == None:
            """
            This should never occure...
            """
            self.data = { 'status': 'error', 'code': self.ERROR_UNCHECKED,  'message': 'Unchecked file' }

        try:
            filename = Directory.objects.get( pk=file.directory.id ).path + '/' + file.filename
            with open( filename, 'rb') as file_to_upload:
                if file.type == file.H5:
                    self.data = HttpResponse( file_to_upload, content_type='application/x-hdf5' )
                elif file.type == file.MUH5:
                    self.data = HttpResponse( file_to_upload, content_type='application/x-hdf5' )
                elif file.type == file.WAV:
                    self.data = HttpResponse( file_to_upload, content_type='audio/x-wav' )
                elif file.type == file.MP4:
                    self.data = HttpResponse( file_to_upload, content_type='video/mp4' )
                else:
                    raise Exception( f"Unknown file format/type: {file.type}" )
                self.data['Content-Disposition'] = f"attachment; filename={file.filename}"

        except Exception as e:
            raise e


class SourceFileSegmentationSerializer:
    """
    Perform segmentation on files
    """

    DEFAULT_FRAME_DURATION = 100
    DEFAULT_CHANNEL_NUMBER = 1
    
    def __init__( self, file: SourceFile, request, algorithm ):

        try:
            """ check query parameters """
            frame_duration = request.query_params.get('frame_duration')
            frame_duration = self.DEFAULT_FRAME_DURATION if frame_duration is None else int( frame_duration )

            channel_id = request.query_params.get('channel_id')
            channel_id = self.DEFAULT_CHANNEL_NUMBER if channel_id is None else int( channel_id )

            """ get file path """
            filename = Directory.objects.get( pk=file.directory.id ).path + '/' + file.filename

            sampling_frequency = file.info['sampling_frequency'] 
            frame_width = int( frame_duration*sampling_frequency/1000 )
            
            if algorithm == 'energy':
                data = compute_energy_from_file( filename, file.type, channel_id=channel_id, frame_duration=frame_duration, power=False, norm=False )
            elif  algorithm == 'power':
                data = compute_energy_from_file( filename, file.type, channel_id=channel_id, frame_duration=frame_duration, power=True, norm=False )
            elif algorithm == 'q50':
                data = compute_q50_from_file( filename, file.type, channel_id=channel_id, frame_duration=frame_duration, norm = False )
            else:
                raise Exception( f"Unknown segmentation algorithm [{algorithm}]" )

            segmentation = {
                'filename': file.filename,
                'filetype': file.WAV,
                'algo': algorithm,
                'sampling_frequency': sampling_frequency,
                'frame_duration': frame_duration,
                'frame_width': frame_width,
                'channel_id': channel_id,
                'data_length': len( data ),
                'max_value': np.amax( data ),
                'min_value': np.amin( data ),
                'data': data
            }
            self.data = Response( segmentation ) 

        except Exception as e:
            raise e 



class SourceFileUploadEnergySerializer:
    """
    Check file existance and compute energy on the given channel 
    """

    ERROR_UNCHECKED = 1
    ERROR_SYSTEM = 2

    def __init__( self, file: SourceFile, channel_id=None, context=None, frame_width=None ):
        if file.integrity == None or file.integrity == False:
            """
            This should never occure...
            """
            self.data = { 'status': 'error', 'code': self.ERROR_UNCHECKED,  'message': 'Unchked file or file integrity problem' }
            return

        try:
            if channel_id is None:
                channel_id = 0

            filename = Directory.objects.get( pk=file.directory.id ).path + '/' + file.filename
            if file.type == file.WAV:
                energy = compute_energy_from_wavfile( filename, channel_id=channel_id, frame_width=frame_width )
                self.data = HttpResponse( energy.tobytes(), headers={
                    'Content-Type': 'application/octet-stream',
                    'Content-Disposition': f"attachment; filename=energy-{Path( file.filename).stem}.data",
                })
            elif file.type == file.MUH5:
                energy = compute_energy_from_muh5file( filename, channel_id=channel_id, frame_width=frame_width )
                self.data = HttpResponse( energy.tobytes(), headers={
                    'Content-Type': 'application/octet-stream',
                    'Content-Disposition': f"attachment; filename=energy-{Path( file.filename).stem}.data",
                })                
            else:
                raise Exception( f"Energy computing on format/type: {file.type} not implemented" )

            #self.data['Content-Disposition'] = f"attachment; filename=energy-{Path( file.filename).stem}.data"

        except Exception as e:
            raise e


class SourceFileUploadRangeSerializer:

    ERROR_UNCHECKED = 1
    ERROR_SYSTEM = 2

    def __init__( self, file: SourceFile, start: float, stop: float, left: int, right: int, context=None, request=None ):
        if file.integrity == None or file.integrity == False :
            """
            This should never occure...
            """
            self.data = { 'status': 'error', 'code': self.ERROR_UNCHECKED,  'message': 'Uncheked file or file integrity problem' }

        try:
            filename = Directory.objects.get( pk=file.directory.id ).path + '/' + file.filename
            if file.type == file.WAV:
                signal = extract_range_from_wavfile( filename, start, stop )
                self.data = HttpResponse( signal.tobytes(), headers={
                    'Content-Type': 'application/octet-stream',
                    'Content-Disposition': f"attachment; filename=range-{Path( file.filename).stem}.data",
                })
            elif file.type == file.MUH5:
                if request is None:
                    # use the mems given as url parameters, left and right 
                    mems = (left, right)
                else:
                    # when passed as query parameters, channels overwrites the usual url parameters  
                    mems = request.query_params.get('channels')
                    if mems is None:
                        mems = (left, right)
                    else:
                        # the form of query param should be: ?channels=1,2,3,4
                        mems = ast.literal_eval( f"({mems})" )

                signal = extract_range_from_muh5file( filename, start, stop, channels=mems )
                self.data = HttpResponse( signal.tobytes(), headers={
                    'Content-Type': 'application/octet-stream',
                    'Content-Disposition': f"attachment; filename=range-{Path( file.filename).stem}.data",
                })                
            else:
                raise Exception( f"Energy computing on format/type: {file.type} not implemented" )            
        except Exception as e:
            raise e


class SourceFileUploadAudioSerializer:

    ERROR_UNCHECKED = 1
    ERROR_SYSTEM = 2

    def __init__( self, file: SourceFile, start: float, stop: float, left: int, right: int, context=None ):
        """
        Audio file downloader serializer

        Parameters
        ===========
        * left (int): left channel number (mems)
        * right (int): right channel number (mems)
        * label_name (str): label name if the audio segment is labelized

        """
        if file.integrity == None or file.integrity == False :
            """
            This should never occure...
            """
            self.data = { 'status': 'error', 'code': self.ERROR_UNCHECKED,  'message': 'Uncheked file or file integrity problem' }

        try:
            filename = Directory.objects.get( pk=file.directory.id ).path + '/' + file.filename
            if file.type == file.WAV:
                signal = genwav_from_range_wavfile( filename, start, stop )
                self.data = HttpResponse( signal, headers={
                    'Content-Type': 'audio/wav',
                    'Content-Disposition': f"attachment; filename=range-{Path( file.filename).stem}.data",
                })
            elif file.type == file.MUH5:
                mems = (left, right)
                signal = genwav_from_range_muh5file( filename, start, stop, channels=mems )
                self.data = HttpResponse( signal, headers={
                    'Content-Type': 'audio/wav',
                    'Content-Disposition': f"attachment; filename={Path( file.filename).stem}-{str(left)}-{str(right)}.data",
                })                
            else:
                raise Exception( f"Energy computing on format/type: {file.type} not implemented" )

        except Exception as e:
            raise e


class DatasetSerializer( serializers.HyperlinkedModelSerializer ):
    channels = serializers.JSONField( initial=list )
    info = serializers.JSONField( initial=dict )
    filename = serializers.CharField( read_only=True )
    filelabelings  = serializers.HyperlinkedRelatedField( many=True, read_only=True, view_name='filelabeling-detail' )
    
    class Meta:
        model = Dataset
        fields = ['id', 'url', 'name', 'code', 'domain', 'labels', 'contexts', 'channels', 'filelabelings', 'filename', 'tags', 'comment', 'info', 'crdate']

    def validate( self, data ):
        """ the default validate function should be OK if channels is set as mandatory in model """
        if not data['channels']:
            """ Should provide channel(s) """
            raise serializers.ValidationError( "Cannot build dataset: no channels (mems number) given." )

        if Dataset.objects.filter( code=data['code'] ).exists():
            """ Datasets cannot have same code """
            raise serializers.ValidationError( f"A dataset '{data['name']}' with same code '{data['code']}' already exists" )

        return data


    def create(self, validated_data):
        """ populate the filelabelinbgs field """

        log.info( f" .Note that label detection is limited to MUH5 files" )

        filelabelings = []
        for label in validated_data['labels']:
            """ search labelized MUH5 files """
            selected = FileLabeling.objects.filter( label=label, sourcefile__type=SourceFile.MUH5 )
            for filelabeling in selected:
                filelabelings.append( filelabeling )
            log.info( f" .Label '{label}': detected {len(selected)} labelized files" )

        if not filelabelings:
            log.info( f" .No labelized file found for dataset {validated_data['name']}" )

        validated_data['filelabelings'] = filelabelings

        """ Create Dataset object """
        dataset = super().create( validated_data )

        return dataset

    
    def update( self, instance: Dataset, validated_data ):
        """ Update is forbidden: database labeling may have change """
        raise serializers.ValidationError( f"Cannot update a dataset. Please create a new one" )


    def remove( self ):
        """
        Remove stored dataset if any
        """
        
        """ get config and the dataset object """
        config = Config.objects.get( active=True )
        dataset: Dataset = self.instance
        
        if dataset.filename:
            """ remove dataset file """
            log.info( f" .Removing stored data for dataset '{dataset.name}'" )
            remove_dataset_muh5_file( f"{config.dataset_path}/{dataset.filename}" )
        else:
            log.info( f" .No stored data to remove for dataset '{dataset.name}'" )


    def store( self ):
        """ 
        Store dataset in H5 file 
        """

        """ get config and dataset object """
        config = Config.objects.get( active=True )
        dataset: Dataset = self.instance

        if dataset.filename:
            """ a dataset file already exist """
            log.info( f" .Seems that a dataset file already exists with name '{dataset.filename}'" )
            log.info( f" .Nothing to do. Please create a new dataset." )
            log.info( f" .Nothing to do. Quitting." )
            raise serializers.ValidationError( f"Cannot store dataset: file already exists. Please create a new dataset instead." )

        """ get signals informations """
        labelings = []
        for filelabeling in dataset.filelabelings.all():
            labelings.append( {
                'start': filelabeling.datetime_start,
                'end': filelabeling.datetime_end,
                'file': f"{filelabeling.sourcefile.directory.path}/{filelabeling.sourcefile.filename}",
                'label': filelabeling.label.code,
                'datetime': filelabeling.sourcefile.datetime,
                'type': filelabeling.sourcefile.type,
                'sample_width': 4 if filelabeling.sourcefile.type==SourceFile.MUH5 else filelabeling.sourcefile.info['sample_width'],
                'sampling_frequency': filelabeling.sourcefile.info['sampling_frequency']                
            } )

        if not labelings:
            raise serializers.ValidationError( "Found no labelized data" )

        """ get meta-data """
        metadata = {
            'name': dataset.name,
            'code': dataset.code,
            'domain': dataset.domain.name,
            'labels': [label.code for label in dataset.labels.all()],
            'channels': dataset.channels,
            'crdate': dataset.crdate
        }

        filename = f"mudset-{dataset.code}-{datetime.strftime( dataset.crdate, '%Y%m%d-%H%M%S' )}.h5"
        log.info( f" .Found {len( labelings )} labelings in dataset" )
        log.info( f" .Store data for dataset '{dataset.name}' in '{filename}'" )

        """ save sound dataset in h5 file """
        try:
            save_dataset_on_muh5_file( f"{config.dataset_path}/{filename}", metadata, labelings )
        except Exception as e:
            raise serializers.ValidationError( f"Storing dataset failed: {e}" )

        """ save the updated dataset object in database """
        dataset.filename = filename
        dataset.save()


class DatasetUploadSerializer:
    """
    Upload serializer for Dataset. Send a http response with file content if dataset has been stored in a file.
    If not, send a http response with a buffer stream as H5 file created on the fly.
    """

    def __init__( self, dataset: Dataset ):
        """
        Download a stored dataset or create an equivalent stream whether dataset has been stored or not
        Request: /dataset/<id>/upload
        """
        
        if dataset.filename:
            """ a stored file exist for dataset """

            """ check file existance """
            config = Config.objects.get( active=True )
            filename = f"{config.dataset_path}/{dataset.filename}"
            if not ospath.exists( filename ):
                log.info( f" .Failed at dataset uploading: file not found" )
                raise Exception( f"Unable to upload: file dataset was not found." )            

            """ download file content """
            log.info( f" .Starting dataset file download..." )
            with open( filename, 'rb') as file_to_upload:
                self.data = HttpResponse( file_to_upload, content_type='application/x-hdf5' )
                self.data['Content-Disposition'] = f"attachment; filename={dataset.name}.h5"

        else:
            """ dataset has not been stored -> build a stream to be sent as H5 file """

            """ get signals informations """
            labelings = []
            for filelabeling in dataset.filelabelings.all():
                labelings.append( {
                    'start': filelabeling.datetime_start,
                    'end': filelabeling.datetime_end,
                    'file': f"{filelabeling.sourcefile.directory.path}/{filelabeling.sourcefile.filename}",
                    'label': filelabeling.label.code,
                    'datetime': filelabeling.sourcefile.datetime,
                    'type': filelabeling.sourcefile.type,
                    'sample_width': 4 if filelabeling.sourcefile.type==SourceFile.MUH5 else filelabeling.sourcefile.info['sample_width'],
                    'sampling_frequency': filelabeling.sourcefile.info['sampling_frequency']                
                } )

            if not labelings:
                raise serializers.ValidationError( "Found no labelized data" )

            """ get meta-data """
            metadata = {
                'name': dataset.name,
                'code': dataset.code,
                'domain': dataset.domain.name,
                'labels': [label.code for label in dataset.labels.all()],
                'channels': dataset.channels,
                'crdate': dataset.crdate
            }

            log.info( f" .Found {len( labelings )} labelings in dataset" )
            log.info( f" .Build stream file for dataset '{dataset.name}'" )

            """ save sound dataset in file stream """
            try:
                h5stream = io.BytesIO()
                save_dataset_on_muh5_file( h5stream, metadata, labelings )
                h5stream.seek( 0 )
                log.info( f" .Starting dataset stream download..." )
                self.data = HttpResponse( h5stream, content_type='application/x-hdf5' )
                self.data['Content-Disposition'] = f"attachment; filename={dataset.name}.h5"

            except Exception as e:
                raise serializers.ValidationError( f"Streaming dataset failed: {e}" )



