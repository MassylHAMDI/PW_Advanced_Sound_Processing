import os
import io
import numpy as np
import wave
import h5py
from datetime import datetime, timedelta
from dateutil import tz
from rest_framework.exceptions import NotFound, server_error
from .models import SourceFile
from megamicros.log import log, logging
from megamicros.muh5 import MuH5

"""
dateutil: https://www.epochconverter.com/timezones
"""
log.setLevel( logging.DEBUG )
tzlocal = tz.gettz( 'CET' )


DEFAULT_ENERGY_SAMPLES = 1000
MEMS_SENSIBILITY = 1/((2**23)*10**(-26/20)/3.17)                            # # MEMs sensibility factor (-26dBFS for 104 dB that is 3.17 Pa)
DEFAULT_MAX_LABEL_SEGS_NUMBER = 1024
DEFAULT_MAX_CONTEXT_SEGS_NUMBER = 1024


def delete_label_on_muh5_file(  filepath: str, label_code: str, segment_code: list ):
    """
    Remove a labeling segment from muh5 file
    A labeling segment is a sound labeling by a label class, a begin/start times and a code called 'segment_code'
    """
    log.info( f" .Opening H5 file {filepath}")
    with h5py.File( filepath, 'a' ) as f:
        """
        Control whether H5 file is a MuH5 file and label group exists
        """
        if not 'muh5' in f:
            raise Exception( f"{filepath} seems not to be a MuH5 file: unrecognized format" )

        muh5 = f['muh5']
        if not 'labels' in muh5:
            raise Exception( f"Label {label_code} not found in file {filepath}" )

        labels = muh5['labels']
        labels_number = labels.attrs['labels_number']
        log.info( f" .Found {labels_number} labels" )

        removed = False
        for c in range( labels_number ):
            dataset = labels[str(c)]
            if dataset.attrs['code'] == label_code:
                log.info( f" .Found label {label_code}" )
                segs_number = dataset.attrs['segs_number']
                for s in range( segs_number ):
                    segment = [int(v) for v in np.array( dataset[s, 2:] )]
                    if segment == segment_code:
                        """
                        Remove the s segment and rearrange the next segments
                        """
                        removed = True
                        log.info( f" .Found segment {segment}. Removing..." )
                        for next in range( segs_number - s - 1 ):
                            """
                            rearrange last segments
                            """
                            dataset[s+next,:] = dataset[s+next+1,:]
                        dataset.attrs['segs_number'] -= 1
                        break
                break                

        if not removed:
            log.info( f" .Delete failed: the label <{label_code}> segment {segment_code} was not found" )
            raise NotFound( detail=f"Delete failed: the label <{label_code}> segment {segment_code} was not found" )



def update_label_on_muh5_file( filepath: str, label_code: str, segment_code: list, datetime_start, datetime_end ):
    """
    Update muh5 file in its labeling part
    """
    log.info( f" .Opening H5 file {filepath}")
    with h5py.File( filepath, 'a' ) as f:
        """
        Control whether H5 file is a MuH5 file and label group exists
        """
        if not 'muh5' in f:
            log.error( f"{filepath} seems not to be a MuH5 file: unrecognized format" )
            raise server_error

        muh5 = f['muh5']
        if not 'contexts' in muh5:
            raise NotFound( f"Label {label_code} not found in file {filepath}" )

        labels = muh5['labels']
        labels_number = labels.attrs['labels_number']
        log.info( f" .Found {labels_number} labels" )

        updated = False
        for c in range( labels_number ):
            dataset = labels[str(c)]
            if dataset.attrs['code'] == label_code:
                log.info( f" .Found label {label_code}" )
                segs_number = dataset.attrs['segs_number']
                for s in range( segs_number ):
                    segment = [int(v) for v in np.array( dataset[s, 2:] )]
                    if segment == segment_code:
                        """
                        found segment to update
                        """
                        updated = True
                        log.info( f" .Found segment {segment}. Updating..." )
                        dataset[s,:] = np.concatenate( ( np.array( (datetime_start, datetime_end) ), np.array( segment_code ).astype( np.float128 ) ) )
                        break
                break
        
        if not updated:
            log.info( f" .Update failed: the label <{label_code}> segment {segment_code} was not found" )
            raise NotFound( detail=f"Update failed: the label <{label_code}> segment {segment_code} was not found" )




def save_label_on_muh5_file( filepath: str, label_code: str, segment_code: list, datetime_start, datetime_end ):
    """
    Save new labeling on muh5 file
    ! > note that np.float128 is not recognized on M2 Mac
    """

    log.info( f" .Opening H5 file {filepath}")
    with h5py.File( filepath, 'a' ) as f:
        """
        Control whether H5 file is a MuH5 file
        """
        if not 'muh5' in f:
            log.error( f"{filepath} seems not to be a MuH5 file: unrecognized format" )
            raise server_error
        
        muh5 = f['muh5']
        if 'labels' in muh5:
            labels = muh5['labels']
            labels_number = labels.attrs['labels_number']
            log.info( f" .Found {labels_number} labels" )
        else:
            """
            Create the sub group labels entry
            """
            log.info( f" .Found no labels. Create the label group...")
            labels = muh5.create_group( 'labels' )
            labels.attrs['labels_number'] = 0
            labels_number = 0

        """
        Check if label exists in file and insert segment
        """
        label_exists = False
        for l in range( labels_number ):
            dataset = labels[str(l)]
            if dataset.attrs['code'] == label_code:
                """
                Code already exists in dataset -> add segment
                """
                segs_number = dataset.attrs['segs_number']
                if segs_number >= dataset.attrs['max_segs']:
                    """
                    Size limit is reached. Resize dataset
                    """
                    dataset.attrs['max_segs'] += 32
                    dataset.resize( (dataset.attrs['max_segs'], 8) )
                
                """
                insert segment with its uuid code as a 6 members array
                """
                log.info( f" .Label {label_code} already exists. Add segment" )
                dataset[segs_number,:] = np.concatenate( ( np.array( (datetime_start, datetime_end) ), np.array( segment_code ).astype( np.float128 ) ) )
                dataset.attrs['segs_number'] += 1
                label_exists = True
                break
        
        if not label_exists:
            """
            Label is not in h5 file -> create a new label dataset and insert segment
            """
            log.info( f" .Label {label_code} do not exists. Create one and add segment" )
            dataset = labels.create_dataset( str(labels_number), (32, 8), maxshape=(DEFAULT_MAX_CONTEXT_SEGS_NUMBER, 8), dtype=np.float128 )
            labels.attrs['labels_number'] += 1
            dataset[0,:] = np.array( (datetime_start, datetime_end) + segment_code )
            dataset.attrs['code'] = label_code
            dataset.attrs['max_segs'] = 32
            dataset.attrs['segs_number'] = 1


def delete_context_on_muh5_file(  filepath: str, context_code: str, segment_code: list ):

    log.info( f" .Opening H5 file {filepath}")
    with h5py.File( filepath, 'a' ) as f:
        """
        Control whether H5 file is a MuH5 file and label group exists
        """
        if not 'muh5' in f:
            raise Exception( f"{filepath} seems not to be a MuH5 file: unrecognized format" )

        muh5 = f['muh5']
        if not 'contexts' in muh5:
            raise Exception( f"Context {context_code} not found in file {filepath}" )

        contexts = muh5['contexts']
        contexts_number = contexts.attrs['contexts_number']
        log.info( f" .Found {contexts_number} contexts" )

        removed = False
        for c in range( contexts_number ):
            dataset = contexts[str(c)]
            if dataset.attrs['code'] == context_code:
                log.info( f" .Found context {context_code}" )
                segs_number = dataset.attrs['segs_number']
                for s in range( segs_number ):
                    segment = [int(v) for v in np.array( dataset[s, 2:] )]
                    if segment == segment_code:
                        """
                        Remove the s segment and rearrange the next segments
                        """
                        removed = True
                        log.info( f" .Found segment {segment}. Removing..." )
                        for next in range( segs_number - s - 1 ):
                            """
                            rearrange last segments
                            """
                            dataset[s+next,:] = dataset[s+next+1,:]
                        dataset.attrs['segs_number'] -= 1
                        break
                break                

        if not removed:
            log.info( f" .Delete failed: the context <{context_code}> segment {segment_code} was not found" )
            raise NotFound( detail=f"Delete failed: the context <{context_code}> segment {segment_code} was not found" )



def update_context_on_muh5_file( filepath: str, context_code: str, segment_code: list, datetime_start, datetime_end ):
    """
    Update muh5 file in its contexting part
    """
    log.info( f" .Opening H5 file {filepath}")
    with h5py.File( filepath, 'a' ) as f:
        """
        Control whether H5 file is a MuH5 file and context group exists
        """
        if not 'muh5' in f:
            log.error( f"{filepath} seems not to be a MuH5 file: unrecognized format" )
            raise server_error

        muh5 = f['muh5']
        if not 'contexts' in muh5:
            raise NotFound( f"Label {context_code} not found in file {filepath}" )

        contexts = muh5['contexts']
        contexts_number = contexts.attrs['contexts_number']
        log.info( f" .Found {contexts_number} contexts" )

        updated = False
        for c in range( contexts_number ):
            dataset = contexts[str(c)]
            if dataset.attrs['code'] == context_code:
                log.info( f" .Found context {context_code}" )
                segs_number = dataset.attrs['segs_number']
                for s in range( segs_number ):
                    segment = [int(v) for v in np.array( dataset[s, 2:] )]
                    if segment == segment_code:
                        """
                        found segment to update
                        """
                        updated = True
                        log.info( f" .Found segment {segment}. Updating..." )
                        dataset[s,:] = np.concatenate( ( np.array( (datetime_start, datetime_end) ), np.array( segment_code ).astype( np.float128 ) ) )
                        break
                break
        
        if not updated:
            log.info( f" .Update failed: the label <{context_code}> segment {segment_code} was not found" )
            raise NotFound( detail=f"Update failed: the label <{context_code}> segment {segment_code} was not found" )




def save_context_on_muh5_file( filepath: str, context_code: str, segment_code: list, datetime_start, datetime_end ):
    """ ! > note that np.float128 is not recognized on M2 Mac """

    log.info( f" .Opening H5 file {filepath}")
    with h5py.File( filepath, 'a' ) as f:
        """
        Control whether H5 file is a MuH5 file
        """
        if not 'muh5' in f:
            log.error( f"{filepath} seems not to be a MuH5 file: unrecognized format" )
            raise server_error
        
        muh5 = f['muh5']
        if 'contexts' in muh5:
            contexts = muh5['contexts']
            contexts_number = contexts.attrs['contexts_number']
            log.info( f" .Found {contexts_number} contexts" )
        else:
            """
            Create the sub group contexts entry
            """
            log.info( f" .Found no contexts. Create the context group...")
            contexts = muh5.create_group( 'contexts' )
            contexts.attrs['contexts_number'] = 0
            contexts_number = 0

        """
        Check if context exists in file and insert segment
        """
        context_exists = False
        for l in range( contexts_number ):
            dataset = contexts[str(l)]
            if dataset.attrs['code'] == context_code:
                """
                Code already exists in dataset -> add segment
                """
                segs_number = dataset.attrs['segs_number']
                if segs_number >= dataset.attrs['max_segs']:
                    """
                    Size limit is reached. Resize dataset
                    """
                    dataset.attrs['max_segs'] += 32
                    dataset.resize( (dataset.attrs['max_segs'], 8) )
                
                """
                insert segment with its uuid code as a 6 members array
                """
                log.info( f" .Context {context_code} already exists. Add segment" )
                dataset[segs_number,:] = np.concatenate( ( np.array( (datetime_start, datetime_end) ), np.array( segment_code ).astype( np.float128 ) ) )
                dataset.attrs['segs_number'] += 1
                context_exists = True
                break
        
        if not context_exists:
            """
            Context is not in h5 file -> create a new context dataset and insert segment
            """
            log.info( f" .Context {context_code} do not exists. Create one and add segment" )
            dataset = contexts.create_dataset( str(contexts_number), (32, 8), maxshape=(DEFAULT_MAX_CONTEXT_SEGS_NUMBER, 8), dtype=np.float128 )
            contexts.attrs['contexts_number'] += 1
            dataset[0,:] = np.array( (datetime_start, datetime_end) + segment_code )
            dataset.attrs['code'] = context_code
            dataset.attrs['max_segs'] = 32
            dataset.attrs['segs_number'] = 1



def extract_range_from_wavfile( wavfilename: str, start: float, stop: float ):
    """
    Extract part of the wav signal according to start and stop (in time) parameters
    
    Parameters
    ----------
    * wavfilename (str): the wav file name with absolute path
    * start: initial time (in seconds)
    * stop: end time (in seconds)
    * return: range signal in np.float32 array format
    """
    with wave.open( wavfilename, 'rb' ) as f:
        sampling_frequency = f.getframerate()
        sample_width = f.getsampwidth()
        channels_number = f.getnchannels()
        samples_number = f.getnframes()
        if sample_width == 1:
            dtype = np.int8
        elif sample_width == 2:
            dtype = np.int16            
        elif sample_width == 4:
            dtype = np.int32
        else:
            raise Exception( f"Unable to process with {sample_width}B data samplewidth" )
        sample_t0 = int( start * sampling_frequency )
        sample_tf = int( stop * sampling_frequency )
        requested_samples_number = sample_tf - sample_t0
        if sample_t0 >= samples_number:
            raise Exception( f"Uncoherent starting position: start time <{start}s> exceed signal duration ({samples_number*sampling_frequency}s)")
        if sample_tf >= samples_number:
            raise Exception( f"Uncoherent end position: stop time <{stop}s> exceed signal duration ({samples_number*sampling_frequency}s)")
        if requested_samples_number <= 0:
            raise Exception( f"Uncoherent time range: start time <{start}s> exceed stop time <{stop}s>")

        f.setpos( sample_t0 )
        sound = np.frombuffer( f.readframes( requested_samples_number ),  dtype=dtype )
        sound = sound.astype( np.float32 )

        return sound/np.amax( sound )


def extract_range_from_muh5file( filename: str, start: float, stop: float, channels: list=(0,), dtype=None ):
    """
    Extract part of the MuH5 signal according to start and stop (in time) parameters
    
    Parameters
    ----------
    * filename (str): the muh5 file name with absolute path
    * start: initial time (in seconds)
    * stop: end time (in seconds)
    * channels: list of requested channels
    * dtype: optionnal, whether data should be return as float32 (default) or int32 (np.int32)
    * return: range signal in np.float32 array format
    """

    log.info( f" .Opening file '{filename}'" )
    with h5py.File( filename, 'r' ) as f:

        """
        Control whether H5 file is a MuH5 file
        """
        if not f['muh5']:
            raise Exception( f"{filename} seems not to be a MuH5 file: unrecognized format" )

        """
        get parameters values on H5 file
        """
        group = f['muh5']
        info = dict( zip( group.attrs.keys(), group.attrs.values() ) )
        sampling_frequency = info['sampling_frequency']
        available_mems = list( info['mems'] )
        mems_number = len( available_mems )
        available_analogs = list( info['analogs'] )
        analogs_number = len( available_analogs )
        duration = info['duration']
        counter = info['counter'] and not info['counter_skip']
        status = True if 'status' in info and info['status'] else False
        available_channels_number = mems_number + analogs_number + ( 1 if counter else 0 ) + ( 1 if status else 0 )
        dataset_length = info['dataset_length']
        dataset_number = info['dataset_number']
        samples_number = dataset_number * dataset_length

        """
        Set mask for channel extracting
        """
        available_channels = [i for i in range( available_channels_number )]
        mask = list( np.isin( available_channels, channels ) )
        if sum(mask) == 0:            
            raise Exception( f"Requested channels not found in {filename}" )

        channels_number = sum( mask )

        """
        Control range values
        """
        sample_t0 = int( start * sampling_frequency )
        sample_tf = int( stop * sampling_frequency )
        requested_samples_number = sample_tf - sample_t0 + 1 
        if sample_t0 >= samples_number:
            raise Exception( f"Uncoherent starting position: start time <{start}s> exceed signal duration ({samples_number*sampling_frequency}s)")
        if sample_tf >= samples_number:
            raise Exception( f"Uncoherent end position: stop time <{stop}s> exceed signal duration ({samples_number*sampling_frequency}s)")
        if requested_samples_number <= 0:
            raise Exception( f"Uncoherent time range: start time <{start}s> exceed stop time <{stop}s>")

        """
        Set index
        """
        dataset_index_t0 = int( sample_t0/dataset_length )
        dataset_index_tf = int( sample_tf/dataset_length )
        dataset_range = dataset_index_tf - dataset_index_t0 + 1

        """
        Extract signal
        """
        sound = np.zeros( (channels_number, requested_samples_number), dtype=np.int32 )
        dest_offset = 0
        dataset_offset = sample_t0%dataset_length

        try: 
            for dataset_index in range( dataset_index_t0, dataset_index_tf+1 ):
                dataset = f['muh5/' + str( dataset_index ) + '/sig']
                dataset_last = dataset_length if sample_tf - dataset_index * dataset_length > dataset_length else sample_tf - dataset_index * dataset_length
                dest_last = dest_offset + dataset_last - dataset_offset #+ 1
                sound[:, dest_offset:dest_last] = np.array( dataset[:] )[mask,dataset_offset:dataset_last]
                dest_offset = dest_last
                dataset_offset = 0

            sound = np.reshape( sound.T, (1, channels_number*requested_samples_number) )
            log.info( f" .Extracted {requested_samples_number} samples of {channels_number} channel(s) signal. Shape is {np.shape(sound)}")

            if dtype == np.int32:
                return sound
            else:
                return sound.astype( np.float32 ) * MEMS_SENSIBILITY

        except Exception as e:
            raise Exception( f"Error while extracting signal from MuH5 file: {e}" )


def compute_q50_from_file( filename:str, filetype:int, channel_id:int|None=1, frame_duration:int|None=None, norm: bool|None = False ) -> np.ndarray:
    """
    Compute Q50 segmentation on file given as input 

    Parameters
    ----------
    * channel_id (int): the channel used for Q50 computing. Default is 1
    * frame_duration (int|None): The Q50 computing frame length in milliseconds.
    * norm (bool): one normalization factor flag
    """

    if filetype == SourceFile.MUH5:

        """ open h5 file and extract signal """
        muh5file = MuH5( filename )

        frame_width = int( frame_duration * muh5file.sampling_frequency // 1000 )
        samples_number = muh5file.samples_number
        channels_number = muh5file.channels_number
        duration = muh5file.duration

        """ get signal """
        sound = muh5file.get_one_channel_signal( channel_id, mems_sensibility=MEMS_SENSIBILITY )

    elif filetype == SourceFile.WAV:

        """ open wav file and extract signal """
        with wave.open( filename, 'rb' ) as f:
            sampling_frequency = f.getframerate()
            sample_width = f.getsampwidth()
            channels_number = f.getnchannels()
            samples_number = f.getnframes()
            if sample_width != 1 and sample_width != 2 and sample_width != 4:
                raise Exception( f"Unable to process with {sample_width}B data samplewidth" )
            dtype = {'1': np.int8, '2': np.int16, '4': np.int32}[str(sample_width)]
            sound = f.readframes( samples_number )

        sound = np.frombuffer( sound, dtype=dtype )
        sound = np.reshape( sound, ( samples_number, channels_number ) )
        if channels_number > 1:
            sound = sound[:,channel_id]
        sound = sound.astype( np.float32 )
        duration = samples_number/sampling_frequency

    """ do some controls """
    if channel_id >= channels_number:
        raise Exception( f"Wrong channel number given ({channel_id}). There are only {channels_number} available channels in file" )

    if frame_width >= samples_number:
        raise Exception ( f"Frame duration is to large ({frame_duration}ms, {frame_width} samples) regarding the signal length ({duration}s, {samples_number} samples)")

    """ reshape for processing on frames """
    frames_number = int( samples_number // frame_width )
    lost_samples_number = int( samples_number % frame_width )
    sound = sound[:samples_number-lost_samples_number]
    sound = np.reshape( sound, (frames_number, frame_width) )

    """ Compute Q50 """
    spec = np.fft.rfft( sound, axis=1 )
    modspec2 = np.abs( spec )    
    modspec2 *= modspec2   
    n_freq = np.size( modspec2,1 )
    frequencies = np.array( [i for i in range( n_freq )] ) * muh5file.sampling_frequency / n_freq / 2
    q50 = np.zeros( frames_number )
    for i in range( frames_number ):
        e = np.abs( spec[i,:] ) * np.abs( spec[i,:] )
        ew = e * frequencies
        q50[i] = np.sum( ew ) / np.sum( e )

    if norm:
        """ normalize to one: max value is 1 """
        q50 = q50 / np.amax( q50 )

    return q50


def compute_energy_from_file( filename:str, filetype:int, channel_id:int|None=1, frame_duration:int|None=None, power: bool|None=False, norm: bool|None = False ) -> np.ndarray:
    """
    Compute energy segmentation on file given as input 

    Parameters
    ----------
    * filename (str): the h5 file name with absolute path
    * filetype (int): the file type (muh5, wav, mp4, etc.)
    * channel_id (int): the channel used for energy computing. Default is 1
    * frame_duration (int|None): The energy computing frame length in milliseconds.
    * power: if true compute the power (mean energy), otherwize compute energy (défault False)
    * norm (bool): one normalization factor flag. If true result is normalized to 1. 
    * return: array of energy computed along <frame_duration> sized windows 
    """

    if filetype == SourceFile.MUH5:

        """ open h5 file and extract signal """
        muh5file = MuH5( filename )

        frame_width = int( frame_duration * muh5file.sampling_frequency // 1000 )
        samples_number = muh5file.samples_number
        channels_number = muh5file.channels_number
        duration = muh5file.duration

        """ get signal """
        sound = muh5file.get_one_channel_signal( channel_id, mems_sensibility=MEMS_SENSIBILITY )

        print( "shape(sound):=", np.shape( sound ) )

    elif filetype == SourceFile.WAV:

        """ open wav file and extract signal """
        with wave.open( filename, 'rb' ) as f:
            sampling_frequency = f.getframerate()
            sample_width = f.getsampwidth()
            channels_number = f.getnchannels()
            samples_number = f.getnframes()
            if sample_width != 1 and sample_width != 2 and sample_width != 4:
                raise Exception( f"Unable to process with {sample_width}B data samplewidth" )
            dtype = {'1': np.int8, '2': np.int16, '4': np.int32}[str(sample_width)]
            sound = f.readframes( samples_number )

        sound = np.frombuffer( sound, dtype=dtype )
        sound = np.reshape( sound, ( samples_number, channels_number ) )
        if channels_number > 1:
            sound = sound[:,channel_id]
        sound = sound.astype( np.float32 )
        duration = samples_number/sampling_frequency

    """ do some controls """
    if channel_id >= channels_number:
        raise Exception( f"Wrong channel number given ({channel_id}). There are only {channels_number} available channels in file" )

    if frame_width >= samples_number:
        raise Exception ( f"Frame duration is to large ({frame_duration}ms, {frame_width} samples) regarding the signal length ({duration}s, {samples_number} samples)")


    """ reshape for processing on frames """
    frames_number = int( samples_number // frame_width )

    lost_samples_number = int( samples_number % frame_width )
    sound = sound[:samples_number-lost_samples_number]
    sound = np.reshape( sound, (frames_number, frame_width) )

    """ Compute energy/power """    
    energy = np.sum( sound*sound, 1 )
    if power:
        """ compute mean energy, that is power """
        energy = energy / frame_width
    if norm:
        """ normalize to one: max value is 1 """
        energy = energy / np.amax( energy )
    
    return energy


def compute_energy_from_muh5file( filename, length=DEFAULT_ENERGY_SAMPLES, channel_id=0, frame_width:int|None=None, power: bool|None=False, norm: bool|None=True  ):
    """
    Compute mean energy on muh5 signal

    Parameters
    ----------
    * filename (str): the h5 file name with absolute path
    * length (int): output energy samples number. Default is 10000
    * channel_id (int): the channel the energy should be computed on. Default is 0
    * frame_duration (int|None): The energy computing frame length in samples number. If given, length is no more used
    * norm: if true result is normed to one: max data value is one, otherwize compute energy or power (default True)
    * power: if true compute the power (mean energy), otherwize compute energy (défault False)
    * return: array of energy computed length times along the signal or computed along <frame_width> sized windows 
    """

    with h5py.File( filename, 'r' ) as f:

        """
        Control whether H5 file is a MuH5 file
        """
        if not f['muh5']:
            raise Exception( f"{filename} seems not to be a MuH5 file: unrecognized format" )

        """
        get parameters values on H5 file
        """
        try:
            group = f['muh5']
            info = dict( zip( group.attrs.keys(), group.attrs.values() ) )
            sampling_frequency = info['sampling_frequency']
            available_mems = list( info['mems'] )
            mems_number = len( available_mems )
            available_analogs = list( info['analogs'] )
            analogs_number = len( available_analogs )
            duration = info['duration']
            counter = info['counter'] and not info['counter_skip']
            status = True if 'status' in info and info['status'] else False
            channels_number = mems_number + analogs_number + ( 1 if counter else 0 ) + ( 1 if status else 0 )
            dataset_length = info['dataset_length']
            dataset_number = info['dataset_number']

            samples_number = dataset_number * dataset_length
            if frame_width is None:                
                frame_width = int( samples_number // length )
            else:
                length = samples_number // frame_width
            lost_samples_number = samples_number % frame_width

        except Exception as e:
            raise Exception( f"Error while reading H5 file {filename}: {e}" )
        
        if channel_id <0:
            raise Exception( f"Incoherent negative channel number requested: <{channel_id}>" )

        if channel_id >= channels_number:
            raise Exception( f"Channel requested <{channel_id}> not found in {filename} which has only <{channels_number}> availables channels" )

        """
        Set mask for channel extracting
        """
        available_channels = [i for i in range( channels_number )]
        mask = list( np.isin( available_channels, list( [channel_id] ) ) )
        
        """
        Extract signal from file
        """
        sound = np.zeros( (1, samples_number), dtype=np.int32 )

        offset = 0
        try:
            for dataset_index in range( dataset_number ):
                dataset = f['muh5/' + str( dataset_index ) + '/sig']
                sound[:,offset:offset+dataset_length] = np.array( dataset[:] )[mask,:]
                offset += dataset_length

            """ convert to float type for mems sensibility normalization """
            sound = sound.astype( np.float32 ) * MEMS_SENSIBILITY

            """
            Compute energy
            """
            sound = sound[:samples_number-lost_samples_number]
            sound = np.reshape( sound, (length, frame_width) )

            energy = np.sum( sound*sound, 1 )
            if power:
                """ compute mean energy, that is power """
                energy = energy / frame_width
            if norm:
                """ normalize to one: max value is 1 """
                energy = energy / np.amax( energy )
            
            return energy

        except Exception as e:
            raise Exception( f"Error while computing energy: {e}" )



def compute_energy_from_wavfile( wavfilename, channel_id=None, length=DEFAULT_ENERGY_SAMPLES, frame_width:int|None=None, power: bool|None=False, norm: bool|None=True ):
    """
    Compute mean energy on wav signal

    Parameters
    ----------
    * wavfilename (str): the wav file name with absolute path
    * channel_id (int): the channel the energy is computed on
    * length (int): output energy samples number
    * frame_width (int|None): The energy computing frame length in samples number. If given, length is no more used
    * norm: if true result is normed to one: max data value is one, otherwize compute energy or power (default True)
    * power: if true compute the power (mean energy), otherwize compute energy (défault False)
    * return: array of energy computed length times along the signal or computed along <frame_width> sized windows 
    """

    with wave.open( wavfilename, 'rb' ) as f:
        sampling_frequency = f.getframerate()
        sample_width = f.getsampwidth()
        channels_number = f.getnchannels()
        samples_number = f.getnframes()
        if sample_width == 1:
            dtype = np.int8
        elif sample_width == 2:
            dtype = np.int16            
        elif sample_width == 4:
            dtype = np.int32
        else:
            raise Exception( f"Unable to process with {sample_width}B data samplewidth" )

        if channel_id >= channels_number:
            raise Exception( f"Channel_id <{channel_id}> is not conform with the signal channels number <{channels_number}>" )

        sound = f.readframes( samples_number )
        sound = np.frombuffer( sound, dtype=dtype )
        sound = np.reshape( sound, ( samples_number, channels_number ) )

        if channels_number > 1:
            sound = sound[:,channel_id]

        if frame_width is None:                
            frame_width = int( samples_number // length )
            if frame_width==0: 
                raise Exception( f"Signal samples number <{samples_number}> less than frame width. Signal is too short for energy computing" )
        else:
            length = samples_number // frame_width

        lost_samples_number = samples_number % frame_width
        sound = sound[:samples_number-lost_samples_number]

        """
        Compute energy
        """
        sound = np.reshape( sound, (length, frame_width) ).astype( np.float32 )
        energy = np.sum( sound*sound, 1 )
        if power:
            """ compute mean energy, that is power """
            energy = energy / frame_width
        if norm:
            """ normalize to one: max value is 1 """
            energy = energy / np.amax( energy )

        return energy



def genwav_from_range_wavfile( wavfilename: str, start: float, stop: float ):
    """
    Extract part of the wav signal according to start and stop (in time) parameters and generate a new wav file
    
    Parameters
    ----------
    * wavfilename (str): the wav file name with absolute path
    * start: initial time (in seconds)
    * stop: end time (in seconds)
    * return: wavfile object in bytes format
    """
    with wave.open( wavfilename, 'rb' ) as f:
        sampling_frequency = f.getframerate()
        sample_width = f.getsampwidth()
        channels_number = f.getnchannels()
        samples_number = f.getnframes()
        if sample_width == 1:
            dtype = np.int8
        elif sample_width == 2:
            dtype = np.int16            
        elif sample_width == 4:
            dtype = np.int32
        else:
            raise Exception( f"Unable to process with {sample_width}B data samplewidth" )
        sample_t0 = int( start * sampling_frequency )
        sample_tf = int( stop * sampling_frequency )
        requested_samples_number = sample_tf - sample_t0
        if sample_t0 >= samples_number:
            raise Exception( f"Uncoherent starting position: start time <{start}s> exceed signal duration ({samples_number*sampling_frequency}s)")
        if sample_tf >= samples_number:
            raise Exception( f"Uncoherent end position: stop time <{stop}s> exceed signal duration ({samples_number*sampling_frequency}s)")
        if requested_samples_number <= 0:
            raise Exception( f"Uncoherent time range: start time <{start}s> exceed stop time <{stop}s>")

        f.setpos( sample_t0 )
        sound = io.BytesIO()
        with wave.open( sound, 'wb' ) as w:
            w.setnchannels( channels_number )
            w.setsampwidth( sample_width )
            w.setframerate( sampling_frequency )
            w.setnframes( requested_samples_number )
            w.writeframes( f.readframes( requested_samples_number ) )
        sound.seek( 0 )

    return sound



def genwav_from_range_muh5file( filename: str, start: float, stop: float, channels: list=(0,) ):
    """
    Extract part of the muh5 signal according to start and stop (in time) parameters and generate a wav file with it
    
    Parameters
    ----------
    * filename (str): the muh5 file name with absolute path
    * start: initial time (in seconds)
    * stop: end time (in seconds)
    * channels (list): channels to extract 
    * return: range signal in np.float32 array format
    """

    with h5py.File( filename, 'r' ) as f:

        """
        Control whether H5 file is a MuH5 file
        """
        if not f['muh5']:
            raise Exception( f"{filename} seems not to be a MuH5 file: unrecognized format" )

        if len( channels ) > 2:
            raise Exception( f"Cannot generate wav file with more than 2 channels ({len( channels)} channels provided: {channels})")

        """
        get parameters values on H5 file
        """
        group = f['muh5']
        info = dict( zip( group.attrs.keys(), group.attrs.values() ) )
        sampling_frequency = info['sampling_frequency']
        available_mems = list( info['mems'] )
        mems_number = len( available_mems )
        available_analogs = list( info['analogs'] )
        analogs_number = len( available_analogs )
        duration = info['duration']
        counter = info['counter'] and not info['counter_skip']
        status = True if 'status' in info and info['status'] else False
        available_channels_number = mems_number + analogs_number + ( 1 if counter else 0 ) + ( 1 if status else 0 )
        dataset_length = info['dataset_length']
        dataset_number = info['dataset_number']
        samples_number = dataset_number * dataset_length

        """
        Set mask for channel extracting
        """
        available_channels = [i for i in range( available_channels_number )]
        mask = list( np.isin( available_channels, channels ) )
        if sum(mask) == 0:            
            raise Exception( f"Requested channels not found in {filename}" )

        channels_number = sum( mask )

        """
        Control range values
        """
        sample_t0 = int( start * sampling_frequency )
        sample_tf = int( stop * sampling_frequency )
        requested_samples_number = sample_tf - sample_t0 + 1 
        if sample_t0 >= samples_number:
            raise Exception( f"Uncoherent starting position: start time <{start}s> exceed signal duration ({samples_number*sampling_frequency}s)")
        if sample_tf >= samples_number:
            raise Exception( f"Uncoherent end position: stop time <{stop}s> exceed signal duration ({samples_number*sampling_frequency}s)")
        if requested_samples_number <= 0:
            raise Exception( f"Uncoherent time range: start time <{start}s> exceed stop time <{stop}s>")

        """
        Set index
        """
        dataset_index_t0 = int( sample_t0/dataset_length )
        dataset_index_tf = int( sample_tf/dataset_length )
        dataset_range = dataset_index_tf - dataset_index_t0 + 1

        """
        Extract signal
        """
        sound = np.zeros( (channels_number, requested_samples_number), dtype=np.int32 )
        dest_offset = 0
        dataset_offset = sample_t0%dataset_length
        try: 
            for dataset_index in range( dataset_index_t0, dataset_index_tf+1 ):

                dataset = f['muh5/' + str( dataset_index ) + '/sig']
                dataset_last = dataset_length if sample_tf - dataset_index * dataset_length > dataset_length else sample_tf - dataset_index * dataset_length
                dest_last = dest_offset + dataset_last - dataset_offset #+ 1
                sound[:, dest_offset:dest_last] = np.array( dataset[:] )[mask,dataset_offset:dataset_last]
                dest_offset = dest_last
                dataset_offset = 0

            sound = np.reshape( sound.T, (1, channels_number*requested_samples_number) )
            log.info( f" .Extracted {requested_samples_number} samples of {channels_number} channel(s) signal. Shape is {np.shape(sound)}")

            wavstream = io.BytesIO()
            with wave.open( wavstream, 'wb' ) as w:
                w.setnchannels( channels_number )
                w.setsampwidth( 2 )
                w.setframerate( sampling_frequency )
                w.setnframes( requested_samples_number )
                w.writeframes( (sound >> 8).astype( np.int16 ) )
            wavstream.seek( 0 )

            return wavstream

        except Exception as e:
            raise Exception( f"Error while extracting signal from MuH5 file: {e}" )


def remove_dataset_muh5_file( filename ):
    """
    Remove data set file
    """

    if os.path.exists( filename ):
        os.remove( filename )
        log.info( f" .'{filename}' file successfully removed" )
    else:
        log.info( f" .'{filename}' file removing failed: no file not found" )


def save_dataset_on_muh5_file( filename: str|io.BytesIO, metadata: dict, labelings: list ):
    
    def check_sampling_properties( labelings: list  ):
        """ 
        Check if data have same sampling characteristics 

        Return:
            Values or false for (sampling_frequency, sample_width)
        """

        sampling_frequency = None
        sample_width = None
        sf_record_flag = sw_record_flag = False
        for labeling in labelings:
            if sampling_frequency is None or sample_width is None:
                """ init values """
                sampling_frequency = labeling['sampling_frequency']
                sample_width = labeling['sample_width']           
            else:
                """ check """
                if labeling['sampling_frequency'] != sampling_frequency:
                    sf_record_flag = True

                if labeling['sample_width'] != sample_width:
                    sw_record_flag = True

                if sf_record_flag and sw_record_flag:
                    """ data are heterogeneous -> end of checking """
                    break

        return (
            sampling_frequency if sf_record_flag==False else False,
            sample_width if sw_record_flag==False else False
        )

    try:

        log.info( f" .Store dataset '{metadata['name']}' in file '{filename}'")

        channels_number = len( metadata['channels'] )
        records_number = len( labelings )
        labels_number = len( metadata['labels'] )

        """ Check if data have same sampling characteristics """
        (sampling_frequency, sample_width) = check_sampling_properties( labelings )


        with h5py.File( filename, 'w' ) as f:
            """ create the root group and set meta-parameters as the root group attributs """
            mudset_group = f.create_group( 'mudset' )
            mudset_group.attrs['name'] = metadata['name']
            mudset_group.attrs['code'] = metadata['code']
            mudset_group.attrs['domain'] = metadata['domain']
            mudset_group.attrs['crdate'] = datetime.strftime( metadata['crdate'], '%Y-%m-%d %H:%M:%S.%f' )
            mudset_group.attrs['timestamp'] = datetime.timestamp( metadata['crdate'] )
            mudset_group.attrs['records_number'] = records_number
            mudset_group.attrs['channels_number'] = channels_number
            mudset_group.attrs['labels_number'] =labels_number
            mudset_group.attrs['sampling_frequency'] = sampling_frequency
            mudset_group.attrs['sample_width'] = sample_width

            """ create label's sub-groups and init records by label counter """
            label_groups = {}
            label_records_counter = {}
            for label in metadata['labels']:
                label_groups[label] = mudset_group.create_group( label )
                label_records_counter[label] = 0

            """ store data in dataset file """
            for i, labeling in enumerate( labelings ):

                label: str = labeling['label']
                label_idx = label_records_counter[label]
                group: h5py.Group = label_groups[label]
                file_datetime: datetime = labeling['datetime']

                """ compute start and stop time indexes from timestamps """
                file_datetime = file_datetime.replace( tzinfo=tzlocal )
                timedate_start = datetime.fromtimestamp( labeling['start'], tz=tzlocal )
                timedate_end = datetime.fromtimestamp( labeling['end'], tz=tzlocal )

                timedelta_start: timedelta = timedate_start - file_datetime
                timedelta_end: timedelta = timedate_end - file_datetime
                index_start = timedelta_start.total_seconds()
                index_end = timedelta_end.total_seconds()

                """ extract signal from original database file """
                if labeling['type'] == SourceFile.MUH5:
                    frame = extract_range_from_muh5file( labeling['file'], index_start, index_end, metadata['channels'], dtype=np.int32 )
                elif labeling['type'] == SourceFile.WAV:
                    frame = extract_range_from_wavfile( labeling['file'], index_start, index_end )
                else:
                    raise Exception( f"Unknown file type '{labeling['type']}'" )

                """ create dataset and store signal (note that data are not compressed -> to to) """
                record_group = group.create_group( str( label_idx ) )
                record_group.attrs['sn'] = np.size( frame ) / channels_number
                record_group.attrs['sf'] = labeling['sampling_frequency'] if not sampling_frequency else 0
                record_group.attrs['sw'] = labeling['sample_width'] if not sample_width else 0
                record_group.create_dataset( 'raw', data=frame )

                """ one more record """
                label_records_counter[label] += 1

            """ update counters """
            for label in metadata['labels']:
                label_groups[label].attrs['rn'] = label_records_counter[label]       


    except Exception as e:
        log.info( f" .Exception: {e}" )

        """ Remove file before quitting """
        if os.path.exists( filename ):
            os.remove( filename )
        raise e

