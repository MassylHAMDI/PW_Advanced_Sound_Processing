# megamicros_aidb/apps/aidb/core/views.py
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
Megamicros AIDB views

MegaMicros documentation is available on https://readthedoc.biimea.io
"""



from datetime import datetime, timedelta
from pytz import timezone
import uuid
from django.shortcuts import render
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, permissions, generics, request
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import renderers, filters, status
from rest_framework.pagination import PageNumberPagination
from .models import Config, Domain, Campaign, Device, Directory, Tagcat, Tag, SourceFile, Context, Label, FileContexting, FileLabeling, Dataset
from .serializers import ConfigSerializer, DomainSerializer, CampaignSerializer, DeviceSerializer, DirectorySerializer
from .serializers import DirectoryFileSerializer, SourceDirectoryCheckSerializer, SourceDirectoryReviseSerializer, TagcatSerializer, TagSerializer
from .serializers import SourceFileSerializer, SourceFileUploadSerializer, SourceFileUploadEnergySerializer, SourceFileUploadRangeSerializer, SourceFileUploadAudioSerializer
from .serializers import ContextSerializer, LabelSerializer, FileLabelingSerializer
from .serializers import DatasetSerializer, DatasetUploadSerializer, SourceFileSegmentationSerializer
from .tools import StandardResultsSetPagination, LargeResultsSetPagination
from .serializers import FileContextingSerializer
from .sp import log, delete_context_on_muh5_file, delete_label_on_muh5_file

# Create your views here.

DEFAULT_TIMEDELTA = 1
DEFAULT_LIMIT_RESPONSE = 10


class ConfigViewSet( viewsets.ModelViewSet ):
    queryset = Config.objects.all()
    serializer_class = ConfigSerializer
    permission_classes = [permissions.IsAuthenticated]


class TagcatViewSet( viewsets.ModelViewSet ):
    queryset = Tagcat.objects.all()
    serializer_class = TagcatSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['name']


class TagViewSet( viewsets.ModelViewSet ):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['name', 'tagcat', 'labels', 'contexts', 'filelabelings']

class DomainViewSet( viewsets.ModelViewSet ):
    """
    The domain let you build several applications in the same database
    """
    queryset = Domain.objects.all()
    serializer_class = DomainSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['name', 'campaigns', 'labels', 'contexts', 'datasets']

class CampaignViewSet( viewsets.ModelViewSet ):
    """
    A campaign is a set of a domain data that have been collected in similar conditions (date and place)
    """
    queryset = Campaign.objects.all()
    serializer_class = CampaignSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['name', 'domain', 'directories']

class DeviceViewSet( viewsets.ModelViewSet ):
    """
    The device is the acquisition system identifier and name
    """
    queryset = Device.objects.all()
    serializer_class = DeviceSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['name', 'type', 'identifier', 'directories']

class DirectoryViewSet( viewsets.ModelViewSet ):
    """
    Directories define all tha absolute data paths where audio/video signals are stored 
    """
    queryset = Directory.objects.all()
    serializer_class = DirectorySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['name', 'path', 'campaign', 'device']

    @action( detail=True, methods=['get'] )
    def check( self, request, pk=None ):
        """
        List all files in that directory
        """
        dir = self.get_object()
        serializer = SourceDirectoryCheckSerializer( dir=dir )
        return Response( serializer.data )

    @action( detail=True, methods=['get'] )
    def install( self, request, pk=None ):
        """
        Update database with all files that are in that directory
        """
        dir = self.get_object()
        serializer = SourceDirectoryReviseSerializer( dir=dir )
        return Response( serializer.data )

    @action( detail=True, methods=['get'] )
    def allfiles( self, request, pk=None ):
        """
        List all installed files in that directory
        """
        dir = self.get_object()
        serializer = DirectoryFileSerializer( dir, many=False, context={'request': request} )
        return Response( serializer.data )

    @action( detail=True, methods=['get'], url_path=r'files/(?P<file_type>wav|muh5|mp4)/datetime/(?P<dt>.+)' )
    def files( self, request, file_type, dt, pk=None, *args, **kwargs ):
        """
        List files of the given type from the given datetime
        * Endpoint: /directory/<directory_id>/files/<wav|muh5|mp4>/datetime/<datetime>
        * datetime format: YYYY-MM-DDThh:mm:ss.uuuuuuZ
        """
        try:
            dt_datetime = timezone( 'Europe/Paris' ).localize( datetime.strptime( dt, '%Y-%m-%dT%H:%M:%S.%fZ' ) )              
            dt_datetime_max = dt_datetime + timedelta( days=DEFAULT_TIMEDELTA )
            dt_max = datetime.strftime( dt_datetime_max, '%Y-%m-%dT%H:%M:%S.%fZ' )

            if file_type == 'wav':
                files = SourceFile.objects.filter( directory=pk, type=SourceFile.WAV, datetime__gte=dt, datetime__lte=dt_max ).order_by('datetime')
            elif file_type == 'muh5':
                files = SourceFile.objects.filter( directory=pk, type=SourceFile.MUH5, datetime__gte=dt, datetime__lte=dt_max ).order_by('datetime')
            elif file_type == 'mp4':
                files = SourceFile.objects.filter( directory=pk, type=SourceFile.MP4, datetime__gte=dt, datetime__lte=dt_max ).order_by('datetime')
            else:
                return Response( { 'status': 'error', 'code': 0, 'detail': f"Unknown <{file_type}> file format"} )

            """
            Limited response to DEFAULT_LIMIT_RESPONSE
            if file_type == 'wav':
                files = SourceFile.objects.filter( directory=pk, type=SourceFile.WAV, datetime__gte=dt, datetime__lte=dt_max ).order_by('datetime')[:DEFAULT_LIMIT_RESPONSE]
            elif file_type == 'muh5':
                files = SourceFile.objects.filter( directory=pk, type=SourceFile.MUH5, datetime__gte=dt, datetime__lte=dt_max ).order_by('datetime')[:DEFAULT_LIMIT_RESPONSE]
            elif file_type == 'mp4':
                files = SourceFile.objects.filter( directory=pk, type=SourceFile.MP4, datetime__gte=dt, datetime__lte=dt_max ).order_by('datetime')[:DEFAULT_LIMIT_RESPONSE]
            else:
                return Response( { 'status': 'error', 'code': 0, 'detail': f"Unknown <{file_type}> file format"} )
            """

            serializer = SourceFileSerializer( files, many=True, context={'request': request}  )
            return Response( serializer.data )
        
        except Exception as e:
            return Response( { 'status': 'error', 'code': 0, 'detail': f"Server error: <{e}>"} )


class SourceFileViewSet( viewsets.ModelViewSet ):
    queryset = SourceFile.objects.all()
    serializer_class = SourceFileSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['filename', 'type', 'datetime', 'directory', 'labels', 'contexts', 'tags']

    @action( detail=True, methods=['get'] )
    def upload( self, request, pk=None ):
        file = self.get_object()
        try:
            serializer = SourceFileUploadSerializer( file=file )
        except Exception as e:
            return Response( { 'status': 'error', 'code': 0, 'message': str( e ) } )

        return serializer.data

    @action( detail=True, methods=['get'], url_path=r'segment/(?P<algo_name>energy|power|q50)' )
    def segment( self, request, algo_name=None, pk=None ):
        """
        Process on file the segmentation algorithm given as argument
        * Endpoint: /sourcefile/<file_id>/segment/<algorithm>/
        * frame_duration (int): time interval for segmentation computation in milliseconds
        """

        file = self.get_object()

        try:
            serializer = SourceFileSegmentationSerializer( file, request, algorithm=algo_name )
        except Exception as e:
            return Response( { 'status': 'error', 'code': 0, 'message': str( e ) } )
        
        return serializer.data


    @action( detail=True, methods=['get'], url_path=r'energy/(?P<channel_id>\d+)' )
    def energy( self, request, channel_id=None, pk=None ):
        """
        Get energy of signal along the given channel.
        Note that <channel_id> could be optionnal with default value to channel 0. Not implemented  
        * Endpoint: /sourcefile/<file_id>/energy/<channel_id>/
        * query param: frame_length (int): energy computing frame width
        """    
        file = self.get_object()
        if channel_id is None:
            channel_id = 0

        try:
            frame_width = request.query_params.get('frame_width')
            if frame_width is not None:
                frame_width = int( frame_width )
            serializer = SourceFileUploadEnergySerializer( file=file, channel_id=int( channel_id ), frame_width=frame_width )
        except Exception as e:
            return Response( { 'status': 'error', 'code': 0, 'message': str( e ) } )

        return serializer.data

    @action( detail=True, methods=['get'], url_path=r'range/(?P<first>\d+(.\d+)?)/(?P<last>\d+(.\d+)?)/channels/(?P<l>\d+)/(?P<r>\d+)' )
    def range(self, request, first, last, l, r, *args, **kwargs):
        """
        Get range signals for MEMs given as query parameter
        
        channels query parameter overwrites the channels/left/right endpoint 
                
        Endpoint parameters
        -------------------
        /sourcefile/range/<first>/<last>/channels/<left>/<right>/<?channels=1,2,3,4,...>
        first: float
            the beginning of the range
        last: float
            the end of the range
        left: int
            left microphone number
        right: int
            right microphone number
        ?channels: list
            liste of MEMs from which to get signal
        """

        file = self.get_object()
        try:
            serializer = SourceFileUploadRangeSerializer( file=file, start=float( first ), stop=float( last ), left=int(l), right=int(r), request=request )
        except Exception as e:
            return Response( { 'status': 'error', 'code': 0, 'message': str( e ) } )
        return serializer.data

    @action( detail=True, methods=['get'], url_path=r'audio/(?P<first>\d+(.\d+)?)/(?P<last>\d+(.\d+)?)/channels/(?P<l>\d+)/(?P<r>\d+)' )
    def audio(self, request, first, last, l, r, *args, **kwargs):
        file = self.get_object()
        try:
            serializer = SourceFileUploadAudioSerializer( file=file, start=float( first ), stop=float( last ), left=int(l), right=int(r) )
        except Exception as e:
            return Response( { 'status': 'error', 'code': 0, 'message': str( e ) } )
        return serializer.data

    @action( detail=False, methods=['get'] )
    def wav( self, request, pk=None ):
        files = SourceFile.objects.filter( type=SourceFile.WAV )
        paginator = PageNumberPagination()
        limit = request.query_params.get('limit')
        paginator.page_size = DEFAULT_LIMIT_RESPONSE if limit is None else int( limit )
        result_page = paginator.paginate_queryset( files, request )
        serializer = SourceFileSerializer( result_page, many=True, context={'request': request}  )
        return paginator.get_paginated_response( serializer.data )

    @action( detail=False, methods=['get'] )
    def muh5( self, request, pk=None ):
        files = SourceFile.objects.filter( type=SourceFile.MUH5 )
        paginator = PageNumberPagination()
        limit = request.query_params.get('limit')
        paginator.page_size = DEFAULT_LIMIT_RESPONSE if limit is None else int( limit )
        result_page = paginator.paginate_queryset( files, request )
        serializer = SourceFileSerializer( result_page, many=True, context={'request': request}  )
        return paginator.get_paginated_response( serializer.data )

    @action( detail=False, methods=['get'] )
    def h5( self, request, pk=None ):
        files = SourceFile.objects.filter( type=SourceFile.H5 )
        paginator = PageNumberPagination()
        limit = request.query_params.get('limit')
        paginator.page_size = DEFAULT_LIMIT_RESPONSE if limit is None else int( limit )
        result_page = paginator.paginate_queryset( files, request )
        serializer = SourceFileSerializer( result_page, many=True, context={'request': request}  )
        return paginator.get_paginated_response( serializer.data )

    @action( detail=False, methods=['get'] )
    def mp4( self, request, pk=None ):
        files = SourceFile.objects.filter( type=SourceFile.MP4 )
        paginator = PageNumberPagination()
        limit = request.query_params.get('limit')
        paginator.page_size = DEFAULT_LIMIT_RESPONSE if limit is None else int( limit )
        result_page = paginator.paginate_queryset( files, request )
        serializer = SourceFileSerializer( result_page, many=True, context={'request': request}  )
        return paginator.get_paginated_response( serializer.data )    




class DomainSourceFileViewSet( viewsets.ModelViewSet ):
    """
    Get files from a given domain, campaign at a given datetime
    """
    queryset = Domain.objects.all()
    serializer_class = DomainSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action( detail=True, methods=['get'], url_path=r'campaign/(?P<campaign_id>[0-9]+)/(?P<file_type>wav|muh5|mp4)/datetime/(?P<dt>.+)' )
    def campaign( self, request, campaign_id, file_type, dt, *args, **kwargs ):
        """
        Get signals of a given campaign by specifying datetime
        * Endpoint: /domainfile/<domain_id>/campaign/<campaign_id>/<wav|muh5|mp4>/datetime/<datetime>
        * datetime format: YYYY-MM-DDThh:mm:ss.uuuuuuZ
        """
        dt_datetime = timezone( 'Europe/Paris' ).localize( datetime.strptime( dt, '%Y-%m-%dT%H:%M:%S.%fZ' ) )              
        dt_datetime_max = dt_datetime + timedelta( days=DEFAULT_TIMEDELTA )
        dt_max = datetime.strftime( dt_datetime_max, '%Y-%m-%dT%H:%M:%S.%fZ' )
        domain = self.get_object()

        if file_type == 'wav':
            files = SourceFile.objects.filter( domain=domain, campaign=campaign_id, type=SourceFile.WAV, datetime__gte=dt, datetime__lte=dt_max ).order_by('datetime')[:DEFAULT_LIMIT_RESPONSE]
        elif file_type == 'muh5':
            files = SourceFile.objects.filter( domain=domain, campaign=campaign_id, type=SourceFile.MUH5, datetime__gte=dt, datetime__lte=dt_max ).order_by('datetime')[:DEFAULT_LIMIT_RESPONSE]
        elif file_type == 'mp4':
            files = SourceFile.objects.filter( domain=domain, campaign=campaign_id, type=SourceFile.MP4, datetime__gte=dt, datetime__lte=dt_max ).order_by('datetime')[:DEFAULT_LIMIT_RESPONSE]
        else:
            return Response( { 'status': 'error', 'code': 0, 'detail': f"Unknown <{file_type}> file format"} )

        serializer = SourceFileSerializer( files, many=True, context={'request': request}  )
        return Response( serializer.data )


    @action( detail=True, methods=['get'], url_path=r'directory/(?P<directory_id>[0-9]+)/campaign/(?P<campaign_id>[0-9]+)/(?P<file_type>wav|muh5|mp4)/datetime/(?P<dt>.+)' )
    def directory( self, request, directory_id, campaign_id, file_type, dt, *args, **kwargs ):
        """
        Get signals of a given campaign and device by specifying datetime
        * Endpoint: /domainfile/<domain_id>/directory/<directory_id>/campaign/<campaign_id>/<wav|muh5|mp4>/datetime/<datetime>
        * datetime format: YYYY-MM-DDThh:mm:ss.uuuuuuZ
        """
        dt_datetime = timezone( 'Europe/Paris' ).localize( datetime.strptime( dt, '%Y-%m-%dT%H:%M:%S.%fZ' ) )              
        dt_datetime_max = dt_datetime + timedelta( days=DEFAULT_TIMEDELTA )
        dt_max = datetime.strftime( dt_datetime_max, '%Y-%m-%dT%H:%M:%S.%fZ' )
        domain = self.get_object()

        if file_type == 'wav':
            files = SourceFile.objects.filter( domain=domain, campaign=campaign_id, pathname=directory_id, type=SourceFile.WAV, datetime__gte=dt, datetime__lte=dt_max ).order_by('datetime')[:DEFAULT_LIMIT_RESPONSE]
        elif file_type == 'muh5':
            files = SourceFile.objects.filter( domain=domain, campaign=campaign_id, pathname=directory_id, type=SourceFile.MUH5, datetime__gte=dt, datetime__lte=dt_max ).order_by('datetime')[:DEFAULT_LIMIT_RESPONSE]
        elif file_type == 'mp4':
            files = SourceFile.objects.filter( domain=domain, campaign=campaign_id, pathname=directory_id, type=SourceFile.MP4, datetime__gte=dt, datetime__lte=dt_max ).order_by('datetime')[:DEFAULT_LIMIT_RESPONSE]
        else:
            return Response( { 'status': 'error', 'code': 0, 'detail': f"Unknown <{file_type}> file format"} )

        serializer = SourceFileSerializer( files, many=True, context={'request': request}  )
        return Response( serializer.data )


class ContextViewset( viewsets.ModelViewSet ):
    queryset = Context.objects.all()
    serializer_class = ContextSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['parent', 'children', 'name', 'code', 'domain', 'type', 'tags']

class FileContextingViewset( viewsets.ModelViewSet ):
    """
    To be removed in next revision
    """
    queryset = FileContexting.objects.all()
    serializer_class = FileContextingSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['sourcefile__filename']

    # We renounce to update origin files when labeling 
    """
    def destroy(self, request: request, *args, **kwargs):
        #delete is not delegated to serializer, so we perform custom logic here
        
        contexting: FileContexting = self.get_object()
        context = contexting.context
        file: SourceFile = contexting.sourcefile

        log.info( f" .Delete requested by {request.user} for context {context.name} in file {file.filename}" )

        delete_context_on_muh5_file( 
            file.directory.path + '/' + file.filename,
            contexting.context.code,
            list( uuid.UUID( contexting.code ).fields )
        )
        log.info( f" .Successfully removed segment {contexting.code}" )
        return super( FileContextingViewset, self).destroy(request, *args, **kwargs )
    """

class LabelViewset( viewsets.ModelViewSet ):
    queryset = Label.objects.all()
    serializer_class = LabelSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['name', 'code', 'parent', 'children', 'domain', 'tags']

    def create( self, request: request, *args, **kwargs):
        log.info( f" .Label create requested by user {request.user}. Request data is: {request.data}, args={args}, kwargs={kwargs}" )

        return super( LabelViewset, self).create( request, *args, **kwargs )

class FileLabelingViewset( viewsets.ModelViewSet ):
    queryset = FileLabeling.objects.all()
    serializer_class = FileLabelingSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['sourcefile', 'label', 'tags', 'contexts']

    # We renounce to update origin files when labeling             
    """
    def destroy(self, request: request, *args, **kwargs):
        # delete is not delegated to serializer, so we perform custom logic here

        labeling: FileLabeling = self.get_object()
        label = labeling.label
        file: SourceFile = labeling.sourcefile

        log.info( f" .Delete requested by {request.user} for context {label.name} in file {file.filename}" )

        delete_label_on_muh5_file( 
            file.directory.path + '/' + file.filename,
            labeling.label.code,
            list( uuid.UUID( labeling.code ).fields )
        )
        log.info( f" .Successfully removed segment {labeling.code}" )
        
        return super( FileLabelingViewset, self).destroy(request, *args, **kwargs )
    """
    
    # Just keep here for having an example of how to do when create crashes for any reason.
    # One interesting features is the way to get info about the on going crash (see the 'serializer.errors' printing bellow)
    """
    def create( self, request: request, *args, **kwargs):
        log.info( f" .FileLabeling create requested by user {request.user}. Request data is: {request.data}, args={args}, kwargs={kwargs}" )

        # create the serializer with data 
        serializer = self.serializer_class( data=request.data )
        # test whteher or not data are valid
        if serializer.is_valid():
            # create the new database entry, as usual
            return super( FileLabelingViewset, self).create( request, *args, **kwargs )
        else:
            # print error and let the creating process crashing...
            print( 'serializers errors: ', serializer.errors)
            return super( FileLabelingViewset, self).create( request, *args, **kwargs )
    """


    @action( detail=False, methods=['get'], url_path=r'label/(?P<label_id>[0-9]+)' )
    def label( self, request, label_id, *args, **kwargs ):
        """
        Get all labelings with label given as parameter
        !! out of date and will be removed in next revision. Use query parameters instead
        """
        labelings = FileLabeling.objects.filter( label_id=label_id )
        paginator = PageNumberPagination()
        limit = request.query_params.get('limit')
        paginator.page_size = DEFAULT_LIMIT_RESPONSE if limit is None else int( limit )
        result_page = paginator.paginate_queryset( labelings, request )
        serializer = FileLabelingSerializer( result_page, many=True, context={'request': request}  )
        return paginator.get_paginated_response( serializer.data )

    @action( detail=False, methods=['get'], url_path=r'sourcefile/(?P<sourcefile_id>[0-9]+)' )
    def sourcefile( self, request, sourcefile_id, *args, **kwargs ):
        """
        Get all labelings with sourcefile given as parameter
        """
        labelings = FileLabeling.objects.filter( sourcefile_id=sourcefile_id )
        paginator = PageNumberPagination()
        limit = request.query_params.get('limit')
        paginator.page_size = DEFAULT_LIMIT_RESPONSE if limit is None else int( limit )
        result_page = paginator.paginate_queryset( labelings, request )
        serializer = FileLabelingSerializer( result_page, many=True, context={'request': request}  )
        return paginator.get_paginated_response( serializer.data )


class DatasetViewSet( viewsets.ModelViewSet ):
    queryset = Dataset.objects.all()
    serializer_class = DatasetSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['name', 'code', 'domain', 'labels', 'contexts', 'filelabelings', 'filename', 'tags']

    def destroy(self, request: request, *args, **kwargs):
        """ 
        delete is not delegated to serializer, so we perform custom logic here 
        """
 
        try:
            dataset: Dataset = self.get_object()
            log.info( f" .Removing dataset '{dataset.name}' for user '{request.user}'" )       
            
            """ remove dataset file if any """
            serializer = DatasetSerializer( dataset, context={'request': request}  )
            serializer.remove()

            """ remove database entry """
            return super( DatasetViewSet, self).destroy( request, *args, **kwargs )
        
        except Exception as e:
            return Response( { 'status': 'error', 'code': 0, 'message': str( e ) } )


    @action( detail=True, methods=['put', 'get'], name='Store dataset' )
    def store( self, request, pk=None ):
        try:
            dataset: Dataset = self.get_object()
            log.info( f" .Store data for dataset '{dataset.name} (pk={pk})'" )
            serializer = DatasetSerializer( dataset, context={'request': request}  )
            serializer.store()
            return Response( serializer.data )

        except Exception as e:
            return Response( { 'status': 'error', 'code': 0, 'message': str( e ) } )
        

    @action( detail=True, methods=['get'] )
    def upload( self, request, pk=None ):
        try:
            dataset = self.get_object()
            serializer = DatasetUploadSerializer( dataset )
            return serializer.data

        except Exception as e:
            return Response( str(e), status=status.HTTP_412_PRECONDITION_FAILED)
            #return Response( { 'status': 'error', 'code': 0, 'message': str( e ) } )
