# Jupyter Notebook interface for the mu32 acquisition system
# Allows to read data from a remote mu32 system, or to play recorded h5 files
#
# Juillet 2022, S. Argentieri, initial version
# Novembre 2023, S. Argentieri, update for new server version

import asyncio
import ipywidgets as widgets                 # For gui widgets in the notebook
import matplotlib.pyplot as plt              # For plotting data
from ipyfilechooser import FileChooser       # gui for selecting h5 files
from megamicros.core.ws import MemsArrayWS   # mu32 interface
from megamicros.core.h5 import MemsArrayH5   # specific mu32 interface for h5 file
import queue                                 # needed for handling exceptions
import paramiko as paramiko
import time
import numpy as np

from megamicros.log import log
log.setLevel( "ERROR" )

class gui_server:
    """ gui_server class, made of ipywidgets widgets for Jupyter notebooks.
        To be used when working with a distant server only.
    """

    def __init__(self, validate_client, startacq_fct, stopacq_fct, startrec_fct, stoprec_fct, sos_fct):
        """Constructor for the gui_server class

        Args:
            validate_client (function): function for validating in the gui the server parameters
            startacq_fct (function): function used by the gui when starting the acquisition
            stopacq_fct (function): function used by the gui when stopping the acquisition
            startrec_fct (function): function used by the gui when starting the data recording
            stoprec_fct (function): function used by the gui when stopping the recording
            sos_fct (function): function used by the gui when sos is required
        """

        # Text widget for visualizing the server IP address
        self.ip = widgets.Text(
            value='10.3.141.1',
            description="Adresse IP:",
            continuous_update=False,
            disabled=False
        )

        # Text widget for visualizing the server port
        self.port = widgets.Text(
            value='9002',
            description="Port:",
            continuous_update=False,
            disabled=False
        )

        # Text widget for choosing the array number
        self.array_nb = widgets.Dropdown(
            options=['F0','F1','F2','F3'],
            value='F0',
            description="N° d'antenne:",
            continuous_update=False,
            disabled=False
        )

        # Text widget for visualizing the sampling frequency
        self.fs = widgets.Text(
            value='',
            description="Fs:",
            continuous_update=False,
            disabled=True
        )

        # Text widget for visualizing the blocksize value
        self.blocksize = widgets.Text(
            value='',
            description="Blocksize:",
            continuous_update=False,
            disabled=True
        )

        # Button widget for validating the server/acquisition configuration
        self.button_connect = widgets.Button(
            description='Confirm'
        )
        self.button_connect.on_click(validate_client)

        # HTML widget for displaying some messages
        self.status = widgets.HTML(
            value='',
            placeholder='Waiting...',
            description='Status:',
        )

        # Button widget for starting the acquisition
        self.button_startacq = widgets.Button(
            description='Start ACQ',
            disabled=True
        )
        self.button_startacq.on_click(startacq_fct)

        # Button widget for stopping the acquisition
        self.button_stopacq = widgets.Button(
            description='Stop ACQ',
            disabled=True
        )
        self.button_stopacq.on_click(stopacq_fct)

        # Button widget for starting the recording
        self.button_startrec = widgets.Button(
            description='Start Recording',
            disabled=True
        )
        self.button_startrec.on_click(startrec_fct)

        # Button widget for stropping the recording
        self.button_stoprec = widgets.Button(
            description='Stop recording',
            disabled=True
        )
        self.button_stoprec.on_click(stoprec_fct)

        # Button widget for SOS
        self.button_sos = widgets.Button(
            description='SOS',
            disabled=False
        )
        self.button_sos.on_click(self.sos)
       
        # HTML widget for displaying about the Raspberry
        self.status_sos = widgets.HTML(
            value='Waiting...',
            placeholder='Waiting...',
            description='Status:',
        )

        # Button widget for starting the server
        self.button_start_srv = widgets.Button(
            description='ADMIN: Start server',
            disabled=False
        )
        self.button_start_srv.on_click(sos_fct)


        # Button widget for stopping the server
        self.button_stop_srv = widgets.Button(
            description='ADMIN: Stop server',
            disabled=False
        )
        self.button_stop_srv.on_click(sos_fct)

        self.passwd = widgets.Password(
            value='',
            description='Password:',
            disabled=False
        )

        # Organization of the widgets in HBox/VBox
        self.ligne1 = widgets.HBox([self.ip, self.port, self.array_nb])
        self.ligne2 = widgets.HBox([self.button_startacq, self.button_stopacq,
                                    self.button_startrec, self.button_stoprec,self.button_connect, self.button_sos])
        self.ligne3 = widgets.HBox([self.fs, self.blocksize, self.status])
        self.ligne4 = widgets.HBox([self.button_start_srv, self.button_stop_srv, self.passwd, self.status_sos])
        # self.ligne4 = widgets.HBox([self.button_stop_srv, self.button_start_srv, self.button_stop_ctrl, 
        #                             self.button_start_ctrl, self.passwd])
        self.ligne4.layout.visibility = 'hidden'
        self.content = widgets.VBox([self.ligne1, self.ligne2, self.ligne3, self.ligne4])

    def update_status(self, message):
        """Update status message in the gui

        Args:
            message (string): message to display in the gui
        """
        self.status.value = message

    def ready_to_start(self, fs, blocksize):
        """Update the gui when validating the parameters
        """
        self.fs.value = str(fs)
        self.blocksize.value = str(blocksize)
        self.ip.disabled = True
        self.port.disabled = True
        self.array_nb.disabled = True
        self.button_connect.disabled = True
        self.button_startacq.disabled = False
        self.button_stopacq.disabled = True
        self.button_startrec.disabled = False
        self.button_stoprec.disabled = True
        self.array_nb.disabled = True
        self.status.value = 'Ready to start acquisition.'

    # def display_parameters(self, fs, blocksize):
    #     """Update the gui when reading acquisition parameters
    #     """
    #     self.fs.value = str(fs)
    #     self.blocksize.value = str(blocksize)

    def start_acq(self):
        """Update the gui when starting the acquisition
        """
        self.button_startacq.disabled = True
        self.button_stopacq.disabled = False
        self.button_startrec.disabled = True
        self.button_stoprec.disabled = True
        self.status.value = 'Acquisition started.'

    def stop_acq(self):
        """Update the gui when stopping the acquisition
        """
        # self.fs.value = ''
        # self.blocksize.value = ''
        self.button_startacq.disabled = False
        self.button_stopacq.disabled = True
        self.button_startrec.disabled = False
        self.button_stoprec.disabled = True
        self.status.value = 'Acquisition stopped.'

    def start_rec(self):
        """Update the gui when starting the recording
        """
        self.button_startacq.disabled = True
        self.button_stopacq.disabled = True
        self.button_startrec.disabled = True
        self.button_stoprec.disabled = False
        self.status.value = 'Recording to file...'

    def stop_rec(self):
        """Update the gui when stopping the recording
        """
        self.button_startacq.disabled = False
        self.button_stopacq.disabled = True
        self.button_startrec.disabled = False
        self.button_stoprec.disabled = True
        self.status.value = 'File saved.'

    def sos(self,button):
        """Update the gui when stopping the recording
        """
        self.fs.value = ''
        self.blocksize.value = ''
        self.button_connect.disabled = True
        self.button_startacq.disabled = True
        #self.button_stopacq.disabled = True
        self.button_startrec.disabled = True
        #self.button_stoprec.disabled = True
        self.button_start_srv.disabled = True
        self.button_stop_srv.disabled = True
        self.status.value = 'SOS mode. For admin only.'
        self.ligne4.layout.visibility = 'visible'

        # Get server/controller status
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(self.ip.value, username='root', password='toto@12!', timeout=5)
        stdin_serv, stdout_serv, stderr_serv = client.exec_command('systemctl is-active megamicros_server.service')
        
        srv = stdout_serv.readlines()
        if srv==['active\n']:
            srv_state = 'OK'
            self.button_start_srv.disabled = True
            self.button_stop_srv.disabled = False
        else:
            srv_state = 'ERROR'
            self.button_start_srv.disabled = False
            self.button_stop_srv.disabled = True

        self.status_sos.value = 'Server = ' + srv_state #+ ' / Controller = ' + ctrl_state
        client.close()

class gui_play:
    """ gui_play class, made of ipywidgets widgets for Jupyter notebooks.
        To be used when trying to play recorder h5 files.
    """

    def __init__(self, play_fct, stopPlay_fct, loadFile_fct):
        """Constructor for the gui_play class.

        Args:
            play_fct (function): function used when playing a file
            stopPlay_fct (function): function used when stopping a playing file
            loadFile_fct (function): function used when loading a h5 file
            read_fct (function): function used when reading the current buffer of a playing file
        """

        # self.file = widgets.FileUpload(
        #     accept='.h5',  # Accepted .h5 file extension only
        #     multiple=False  # True to accept multiple files upload, else False
        # )

        # FileChooser widget for loading the H5 file to be played
        self.file = FileChooser('')
        self.file.filter_pattern = '*.h5'
        self.file.register_callback(loadFile_fct)

        # Text widget for visualizing the sampling frequency from the loaded file
        self.fs = widgets.Text(
            value='',
            description="Fs:",
            continuous_update=False,
            disabled=True
        )

        # Text widget for visualizing the blocksize value
        self.blocksize = widgets.Text(
            value='2048',
            description="Blocksize:",
            continuous_update=False,
            disabled=False
        )

        # Button widget for playing file
        self.button_startplay = widgets.Button(
            description='Play file',
            disabled=True
        )
        self.button_startplay.on_click(play_fct)

        # Button widget for stopping the file
        self.button_stopplay = widgets.Button(
            description='Stop',
            disabled=True,
        )
        self.button_stopplay.on_click(stopPlay_fct)
        #self.button_stopplay.layout.visibility = "hidden"

        # HTML widget for displaying some messages
        self.status = widgets.HTML(
            value='',
            placeholder='Waiting...',
            description='Status:',
        )

        # Organization of the widgets in HBox/VBox
        self.ligne1 = widgets.HBox([self.file])
        self.ligne2 = widgets.HBox([self.fs, self.blocksize, self.status])
        self.ligne3 = widgets.HBox(
            [self.button_startplay, self.button_stopplay])
        self.content = widgets.VBox([self.ligne1, self.ligne2, self.ligne3])

    def update_data_info(self, fs, duration):
        """Update the gui when loading the file
        """
        self.fs.value = fs
        self.blocksize.disabled = False
        self.button_startplay.disabled = False
        self.button_stopplay.disabled = True
        self.status.value = 'File duration = ' + duration + 's.'

    def start_read(self):
        """Update the gui when starting the file
        """
        self.blocksize.disabled = True
        self.button_startplay.disabled = True
        self.button_stopplay.disabled = False
        self.status.value = 'Reading file'

    def stop_read(self):
        """Update the gui when stopping the file
        """
        self.blocksize.disabled = False
        self.button_startplay.disabled = False
        self.button_stopplay.disabled = True
        self.status.value = 'Reading stopped'

    def update_status(self, message):
        """Update status message in the gui

        Args:
            message (string): message to display in the gui
        """
        self.status.value = message


class array():
    """ array class, interfacing a Jupyter Notebook with a Mu32 array
    """

    fs = 0
    blocksize = 0

    def __init__(self, type):
        """Constructor of the array class.

        Args:
            type (string): type of interface, to be chosen among 'server' or 'play'.
        """

        # If one whishes to connect to a real server, initialize the corresponding gui
        if type == 'server':
            self.gui = gui_server(self.validateAcq_fct, self.startacq_fct,
                                  self.stopacq_fct, self.startrec_fct, self.stoprec_fct,
                                  self.sos_fct)
        
        # If one whishes to play a recorded h5 file, initialize the corresponding gui
        elif type == 'play':            
            self.gui = gui_play(self.play_fct, self.stopplay_fct, self.loadFile_fct)
        
        # Else ... this is an error.
        else:
            self.gui = []
            print('ERROR: server type must be selected among /server/ or /play/.')
            return

        # Actually display the corresponding gui in the Jupyter Notebook
        display(self.gui.content)


    async def validateAcq_fct_settings( self ):
        """ Get settings from server and display the corresponding options in the gui """

        # Create Future for getting asynchronous results  
        settings_future = asyncio.Future()

        # Get settings using the async mu32 entry and providing the future coroutine
        task = asyncio.create_task( self.mu32.async_settings( settings_future ) )
        settings = await settings_future
        
        # set local attributes
        self.fs = settings["sampling_frequency"]
        self.blocksize = settings["frame_length"]
        self.mems_nb=len(self.mems_list)
        self.interspace = 0.06

        # Activate/Deactivate the corresponding widgets in the gui
        self.gui.ready_to_start(self.fs, self.blocksize)


    def validateAcq_fct(self, button):
        """Initialize the object allowing to connect to the remote server, and display the 
           corresponding options in the gui.

        Args:
            button (ipywidgets button object): button used in the gui to launch this function.
        """

        # Create the mu32 object from the IP/PORT of the remote server
        self.mu32 = MemsArrayWS(self.gui.ip.value, port=self.gui.port.value )

        if self.gui.array_nb.value == 'F0':
            self.mems_list = [i for i in range(8)]
        elif self.gui.array_nb.value == 'F1':
            self.mems_list = [i for i in range(8,16)]
        elif self.gui.array_nb.value == 'F2':
            self.mems_list = [i for i in range(16,24)]
        elif self.gui.array_nb.value == 'F3':
            self.mems_list = [i for i in range(24,32)]
        else:
            print('ERROR: bad array number selected.')
            return

        # Get remote settings
        #self.mu32.settings()

        #### mu32.setting is an async task whose result is not available in jupyer main exec loop
        #### so, for now, hardecode the sampling freq and blocksize as set by the master
        #### on the server.
        #### Parameters are set in /root/megamicros-server/build/src/mbs-server.json on the
        #### server. The same values must be used here.

        # Populate attributes with the acquisition parameters
        #self.fs = 20000
        #self.blocksize=1024

        # Start async task to get settings from the server
        # All local attribute settings should be done in that task otherwise results would not be available before the end of the current cell execution
        task = asyncio.create_task( self.validateAcq_fct_settings() )

        # !! Nothing more to do after this point !!


    def startacq_fct(self, button):
        """Launch the acquisition on the remote server, and display the corresponding gui options.

        Args:
            button (ipywidgets button object): button used in the gui to launch this function.
        """
        try:
            # Launch the acquisition from the remote server
            self.mu32.run(
                mems = self.mems_list,
                duration=0,
                signal_q_size = 1,
                job='listen')

            # Activate/Deactivate the corresponding widgets in the gui
            self.gui.start_acq()

        except Exception as e:
            self.gui.update_status('Aborting: ' + str( e ))

    def stopacq_fct(self, button):
        """Stop the acquisition on the remote server and display the corresponding gui options.

        Args:
            button (ipywidgets button object): button used in the gui to launch this function.
        """
        # Stop the acquisition of the remote server
        self.mu32.halt()
        # Activate/Deactivate the corresponding widgets in the gui
        self.gui.stop_acq()

    def startrec_fct(self, button):
        """Start the recording from the remote server into a local h5 file.

        Args:
            button (ipywidgets button object): button used in the gui to launch this function.
        """
        try:
            
            # Activate/Deactivate the corresponding widgets in the gui
            self.gui.start_rec()

            # Launch the acquisition from the remote server
            self.mu32.run(
                mems = self.mems_list,
                duration=0,
                h5_recording=True,          # H5 recording ON
                h5_pass_through=False,      # perform F5 recording locally
                h5_rootdir='./',            # directory where to save file
                h5_compressing=False,       # Use compression or not
                signal_q_size = 0,
                job='listen'
            )
            self.mu32.h5_start()
            # self.mu32.wait()

        except Exception as e:
            self.gui.update_status('Aborting: ' + e)

    def stoprec_fct(self, button):
        """Stop the recording from the remote server.

        Args:
            button (ipywidgets button object): button used in the gui to launch this function.
        """
        # Stop recording
        self.mu32.h5_stop()
        self.mu32.halt()
        # Activate/Deactivate the corresponding widgets in the gui
        self.gui.stop_rec()

    def read(self):
        """Read current audio buffer. The buffer is also available in the .m attribute of the 
           array object.

        Returns:
            np.array: current audio buffer of size nb_mic x blocksize
        """
        try:
            # Read last buffer
            #self.m = self.mu32.signal_q.get(block=True, timeout=2) * self.mu32.sensibility
            self.m = self.mu32.signal_q.get(timeout = 5).astype( np.float32 ) * self.mu32.sensibility
            # Return array
            return self.m
        except queue.Empty:
            self.gui.update_status('ERROR: No data available')
            return

    def loadFile_fct(self, file):
        """Get path of the H5 file te be played, sets the corresponding attributes and change the
           gui accordingly.

        Args:
            file (ipywidgets file object): widget used in the gui to select the H5 file.
        """
        # Update parameters attributes in the object from the values in the file gui object
        self.filename = file.selected
        # Intialize the mu32 object with the data in the file
        self.mu32 = MemsArrayH5(filename=file.selected)
        # Update others parameters
        self.fs = self.mu32.sampling_frequency
        self.file_duration = self.mu32.file_duration
        self.interspace = 0.06
        # Update the gui with the parameters readed in the file
        self.gui.update_data_info(str(self.fs), str(self.file_duration))

    def play_fct(self, button):
        """Play the H5 file, sets the corresponding attributes and change the
           gui accordingly.

        Args:
            button (ipywidgets button object): button used in the gui to launch this function.
        """

        self.blocksize=int(self.gui.blocksize.value)
        self.mems_nb=len(self.mu32.mems)
        # Run antenna
        self.mu32.run(
            mems = self.mu32.available_mems,
            #duration=self.file_duration,
            duration=0,
            frame_length=self.blocksize,
            counter_skip = True,
            signal_q_size = 0,
            datatype='int32'
        )

        self.gui.start_read()

    def stopplay_fct(self, button):
        """NOT NEEDED ANYMORE ????
        """
        self.mu32.stop() # ?????????
        self.gui.stop_read()

    def sos_fct(self, button):
        """SOS mode, which allows to start/stop the server and controller on the raspberry. Avoid
           rebooting the raspberry when srv/ctrl are down.

        Args:
            button (ipywidgets button object): button used in the gui to launch this function.
        """

        if self.gui.passwd.value=='':
            print('ERROR: please indicate the password to launch the command.')
            return

        client = paramiko.SSHClient()
        #client.load_system_host_keys() 
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(self.gui.ip.value, username='root', password=self.gui.passwd.value, timeout=5)
        if button.description=='ADMIN: Stop server':
            command = 'systemctl stop megamicros_server'
            self.gui.button_start_srv.disabled = False
            self.gui.button_stop_srv.disabled = True
        elif button.description=='ADMIN: Start server':
            command = 'systemctl start megamicros_server'
            self.gui.button_start_srv.disabled = True
            self.gui.button_stop_srv.disabled = False
        else:
            command = 'ls'
            print('Unkown button...')

        client.exec_command(command)
        client.close()

