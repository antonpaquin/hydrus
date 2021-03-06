import cStringIO
import ClientConstants as CC
import ClientNetworkingContexts
import ClientNetworkingDomain
import HydrusConstants as HC
import HydrusData
import HydrusExceptions
import HydrusGlobals as HG
import HydrusNetworking
import os
import requests
import threading
import traceback
import time

def ConvertStatusCodeAndDataIntoExceptionInfo( status_code, data, is_hydrus_service = False ):
    
    error_text = data
    
    if len( error_text ) > 1024:
        
        large_chunk = error_text[:4096]
        
        smaller_chunk = large_chunk[:256]
        
        HydrusData.DebugPrint( large_chunk )
        
        error_text = 'The server\'s error text was too long to display. The first part follows, while a larger chunk has been written to the log.'
        error_text += os.linesep
        error_text += smaller_chunk
        
    
    if status_code == 304:
        
        eclass = HydrusExceptions.NotModifiedException
        
    elif status_code == 401:
        
        eclass = HydrusExceptions.PermissionException
        
    elif status_code == 403:
        
        eclass = HydrusExceptions.ForbiddenException
        
    elif status_code == 404:
        
        eclass = HydrusExceptions.NotFoundException
        
    elif status_code == 419:
        
        eclass = HydrusExceptions.SessionException
        
    elif status_code == 426:
        
        eclass = HydrusExceptions.NetworkVersionException
        
    elif status_code == 509:
        
        eclass = HydrusExceptions.BandwidthException
        
    elif status_code >= 500:
        
        if is_hydrus_service and status_code == 503:
            
            eclass = HydrusExceptions.ServerBusyException
            
        else:
            
            eclass = HydrusExceptions.ServerException
            
        
    else:
        
        eclass = HydrusExceptions.NetworkException
        
    
    e = eclass( error_text )
    
    return ( e, error_text )
    
class NetworkJob( object ):
    
    IS_HYDRUS_SERVICE = False
    
    def __init__( self, method, url, body = None, referral_url = None, temp_path = None ):
        
        if HG.network_report_mode:
            
            HydrusData.ShowText( 'Network Job: ' + method + ' ' + url )
            
        
        self.engine = None
        
        self._lock = threading.Lock()
        
        self._method = method
        self._url = url
        self._body = body
        self._referral_url = referral_url
        self._temp_path = temp_path
        
        self._files = None
        self._for_login = False
        
        self._current_connection_attempt_number = 1
        
        self._additional_headers = {}
        
        self._creation_time = HydrusData.GetNow()
        
        self._bandwidth_tracker = HydrusNetworking.BandwidthTracker()
        
        self._wake_time = 0
        
        self._content_type = None
        
        self._stream_io = cStringIO.StringIO()
        
        self._error_exception = Exception( 'Exception not initialised.' ) # PyLint hint, wew
        self._error_exception = None
        self._error_text = None
        
        self._is_done_event = threading.Event()
        
        self._is_done = False
        self._is_cancelled = False
        self._bandwidth_manual_override = False
        self._bandwidth_manual_override_delayed_timestamp = None
        
        self._last_time_ongoing_bandwidth_failed = 0
        
        self._status_text = u'initialising\u2026'
        self._num_bytes_read = 0
        self._num_bytes_to_read = 1
        
        self._file_import_options = None
        
        self._network_contexts = self._GenerateNetworkContexts()
        
        ( self._session_network_context, self._login_network_context ) = self._GenerateSpecificNetworkContexts()
        
    
    def _CanReattemptConnection( self ):
        
        max_attempts_allowed = 3
        
        return self._current_connection_attempt_number <= max_attempts_allowed
        
    
    def _CanReattemptRequest( self ):
        
        if self._method == 'GET':
            
            max_attempts_allowed = 5
            
        elif self._method == 'POST':
            
            max_attempts_allowed = 1
            
        
        return self._current_connection_attempt_number <= max_attempts_allowed
        
    
    def _GenerateNetworkContexts( self ):
        
        network_contexts = []
        
        network_contexts.append( ClientNetworkingContexts.GLOBAL_NETWORK_CONTEXT )
        
        domain = ClientNetworkingDomain.ConvertURLIntoDomain( self._url )
        domains = ClientNetworkingDomain.ConvertDomainIntoAllApplicableDomains( domain )
        
        network_contexts.extend( ( ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_DOMAIN, domain ) for domain in domains ) )
        
        return network_contexts
        
    
    def _GenerateSpecificNetworkContexts( self ):
        
        # we always store cookies in the larger session (even if the cookie itself refers to a subdomain in the session object)
        # but we can login to a specific subdomain
        
        domain = ClientNetworkingDomain.ConvertURLIntoDomain( self._url )
        domains = ClientNetworkingDomain.ConvertDomainIntoAllApplicableDomains( domain )
        
        session_network_context = ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_DOMAIN, domains[-1] )
        login_network_context = ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_DOMAIN, domain )
        
        return ( session_network_context, login_network_context )
        
    
    def _SendRequestAndGetResponse( self ):
        
        with self._lock:
            
            session = self._GetSession()
            
            method = self._method
            url = self._url
            data = self._body
            files = self._files
            
            headers = self.engine.domain_manager.GetHeaders( self._network_contexts )
            
            if self.IS_HYDRUS_SERVICE:
                
                headers[ 'User-Agent' ] = 'hydrus client/' + str( HC.NETWORK_VERSION )
                
            
            if self._referral_url is not None:
                
                headers[ 'referer' ] = self._referral_url
                
            
            for ( key, value ) in self._additional_headers.items():
                
                headers[ key ] = value
                
            
            self._status_text = u'sending request\u2026'
            
        
        connect_timeout = HG.client_controller.new_options.GetInteger( 'network_timeout' )
        
        read_timeout = connect_timeout * 6
        
        response = session.request( method, url, data = data, files = files, headers = headers, stream = True, timeout = ( connect_timeout, read_timeout ) )
        
        return response
        
    
    def _GetSession( self ):
        
        return self.engine.session_manager.GetSession( self._session_network_context )
        
    
    def _IsCancelled( self ):
        
        if self._is_cancelled:
            
            return True
            
        
        if self.engine.controller.ModelIsShutdown():
            
            return True
            
        
        return False
        
    
    def _IsDone( self ):
        
        if self._is_done:
            
            return True
            
        
        if self.engine.controller.ModelIsShutdown():
            
            return True
            
        
        return False
        
    
    def _ObeysBandwidth( self ):
        
        if self._bandwidth_manual_override:
            
            return False
            
        
        if self._bandwidth_manual_override_delayed_timestamp is not None and HydrusData.TimeHasPassed( self._bandwidth_manual_override_delayed_timestamp ):
            
            return False
            
        
        if self._method == 'POST':
            
            return False
            
        
        if self._for_login:
            
            return False
            
        
        return True
        
    
    def _OngoingBandwidthOK( self ):
        
        now = HydrusData.GetNow()
        
        if now == self._last_time_ongoing_bandwidth_failed: # it won't have changed, so no point spending any cpu checking
            
            return False
            
        else:
            
            result = self.engine.bandwidth_manager.CanContinueDownload( self._network_contexts )
            
            if not result:
                
                self._last_time_ongoing_bandwidth_failed = now
                
            
            return result
            
        
    
    def _ReadResponse( self, response, stream_dest, max_allowed = None ):
        
        with self._lock:
            
            if self._content_type is not None and self._content_type in HC.mime_enum_lookup:
                
                mime = HC.mime_enum_lookup[ self._content_type ]
                
            else:
                
                mime = None
                
            
            if 'content-length' in response.headers:
            
                self._num_bytes_to_read = int( response.headers[ 'content-length' ] )
                
                if max_allowed is not None and self._num_bytes_to_read > max_allowed:
                    
                    raise HydrusExceptions.NetworkException( 'The url was apparently ' + HydrusData.ConvertIntToBytes( self._num_bytes_to_read ) + ' but the max network size for this type of job is ' + HydrusData.ConvertIntToBytes( max_allowed ) + '!' )
                    
                
                if self._file_import_options is not None:
                    
                    certain = True
                    
                    self._file_import_options.CheckNetworkDownload( mime, self._num_bytes_to_read, certain )
                    
                
            else:
                
                self._num_bytes_to_read = None
                
            
        
        for chunk in response.iter_content( chunk_size = 65536 ):
            
            if self._IsCancelled():
                
                return
                
            
            stream_dest.write( chunk )
            
            chunk_length = len( chunk )
            
            with self._lock:
                
                self._num_bytes_read += chunk_length
                
                if max_allowed is not None and self._num_bytes_read > max_allowed:
                    
                    raise HydrusExceptions.NetworkException( 'The url exceeded the max network size for this type of job, which is ' + HydrusData.ConvertIntToBytes( max_allowed ) + '!' )
                    
                
                if self._file_import_options is not None:
                    
                    certain = False
                    
                    self._file_import_options.CheckNetworkDownload( mime, self._num_bytes_to_read, certain )
                    
                
            
            self._ReportDataUsed( chunk_length )
            self._WaitOnOngoingBandwidth()
            
            if HG.view_shutdown:
                
                raise HydrusExceptions.ShutdownException()
                
            
        
        if self._num_bytes_to_read is not None and self._num_bytes_read < self._num_bytes_to_read * 0.8:
            
            raise HydrusExceptions.ShouldReattemptNetworkException( 'Was expecting ' + HydrusData.ConvertIntToBytes( self._num_bytes_to_read ) + ' but only got ' + HydrusData.ConvertIntToBytes( self._num_bytes_read ) + '.' )
            
        
    
    def _ReportDataUsed( self, num_bytes ):
        
        self._bandwidth_tracker.ReportDataUsed( num_bytes )
        
        self.engine.bandwidth_manager.ReportDataUsed( self._network_contexts, num_bytes )
        
    
    def _SetCancelled( self ):
        
        self._is_cancelled = True
        
        self._SetDone()
        
    
    def _SetError( self, e, error ):
        
        self._error_exception = e
        self._error_text = error
        
        self._SetDone()
        
    
    def _SetDone( self ):
        
        self._is_done = True
        
        self._is_done_event.set()
        
    
    def _Sleep( self, seconds ):
        
        self._wake_time = HydrusData.GetNow() + seconds
        
    
    def _WaitOnOngoingBandwidth( self ):
        
        while not self._OngoingBandwidthOK() and not self._IsCancelled():
            
            time.sleep( 0.1 )
            
        
    
    def AddAdditionalHeader( self, key, value ):
        
        with self._lock:
            
            self._additional_headers[ key ] = value
            
        
    
    def BandwidthOK( self ):
        
        with self._lock:
            
            if self._ObeysBandwidth():
                
                result = self.engine.bandwidth_manager.TryToStartRequest( self._network_contexts )
                
                if result:
                    
                    self._bandwidth_tracker.ReportRequestUsed()
                    
                else:
                    
                    bandwidth_waiting_duration = self.engine.bandwidth_manager.GetWaitingEstimate( self._network_contexts )
                    
                    will_override = self._bandwidth_manual_override_delayed_timestamp is not None
                    
                    override_coming_first = False
                    
                    if will_override:
                        
                        override_waiting_duration = HydrusData.GetNow() - self._bandwidth_manual_override_delayed_timestamp
                        
                        override_coming_first = override_waiting_duration < bandwidth_waiting_duration
                        
                    
                    if override_coming_first:
                        
                        waiting_duration = override_waiting_duration
                        
                        prefix = 'overriding bandwidth '
                        
                        waiting_str = HydrusData.ConvertTimestampToPrettyPending( self._bandwidth_manual_override_delayed_timestamp )
                        
                    else:
                        
                        waiting_duration = bandwidth_waiting_duration
                        
                        prefix = 'bandwidth free '
                        
                        waiting_str = HydrusData.ConvertTimestampToPrettyPending( HydrusData.GetNow() + waiting_duration )
                        
                    
                    if waiting_duration < 2:
                        
                        waiting_str = 'imminently'
                        
                    
                    self._status_text = prefix + waiting_str + u'\u2026'
                    
                    if waiting_duration > 1200:
                        
                        self._Sleep( 30 )
                        
                    elif waiting_duration > 120:
                        
                        self._Sleep( 10 )
                        
                    elif waiting_duration > 10:
                        
                        self._Sleep( 1 )
                        
                    
                
                return result
                
            else:
                
                self._bandwidth_tracker.ReportRequestUsed()
                
                self.engine.bandwidth_manager.ReportRequestUsed( self._network_contexts )
                
                return True
                
            
        
    
    def Cancel( self ):
        
        with self._lock:
            
            self._status_text = 'cancelled!'
            
            self._SetCancelled()
            
        
    
    def CanValidateInPopup( self ):
        
        with self._lock:
            
            return self.engine.domain_manager.CanValidateInPopup( self._network_contexts )
            
        
    
    def CheckCanLogin( self ):
        
        with self._lock:
            
            if self._for_login:
                
                raise HydrusExceptions.LoginException( 'Login jobs should not be asked if they can login!' )
                
            else:
                
                return self.engine.login_manager.CheckCanLogin( self._login_network_context )
                
            
        
    
    def GenerateLoginProcess( self ):
        
        with self._lock:
            
            if self._for_login:
                
                raise Exception( 'Login jobs should not be asked to generate login processes!' )
                
            else:
                
                return self.engine.login_manager.GenerateLoginProcess( self._login_network_context )
                
            
        
    
    def GenerateValidationPopupProcess( self ):
        
        with self._lock:
            
            return self.engine.domain_manager.GenerateValidationPopupProcess( self._network_contexts )
            
        
    
    def GetContent( self ):
        
        with self._lock:
            
            self._stream_io.seek( 0 )
            
            return self._stream_io.read()
            
        
    
    def GetContentType( self ):
        
        with self._lock:
            
            return self._content_type
            
        
    
    def GetCreationTime( self ):
        
        with self._lock:
            
            return self._creation_time
            
        
    
    def GetErrorException( self ):
        
        with self._lock:
            
            return self._error_exception
            
        
    
    def GetErrorText( self ):
        
        with self._lock:
            
            return self._error_text
            
        
    
    def GetNetworkContexts( self ):
        
        with self._lock:
            
            return list( self._network_contexts )
            
        
    
    def GetStatus( self ):
        
        with self._lock:
            
            return ( self._status_text, self._bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, 1 ), self._num_bytes_read, self._num_bytes_to_read )
            
        
    
    def GetTotalDataUsed( self ):
        
        with self._lock:
            
            return self._bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, None )
            
        
    
    def GetURL( self ):
        
        with self._lock:
            
            return self._url
            
        
    
    def HasError( self ):
        
        with self._lock:
            
            return self._error_exception is not None
            
        
    
    def IsAsleep( self ):
        
        with self._lock:
            
            return not HydrusData.TimeHasPassed( self._wake_time )
            
        
    
    def IsCancelled( self ):
        
        with self._lock:
            
            return self._IsCancelled()
            
        
    
    def IsDone( self ):
        
        with self._lock:
            
            return self._IsDone()
            
        
    
    def IsValid( self ):
        
        with self._lock:
            
            return self.engine.domain_manager.IsValid( self._network_contexts )
            
        
    
    def NeedsLogin( self ):
        
        with self._lock:
            
            if self._for_login:
                
                return False
                
            else:
                
                return self.engine.login_manager.NeedsLogin( self._login_network_context )
                
            
        
    
    def NoEngineYet( self ):
        
        return self.engine is None
        
    
    def ObeysBandwidth( self ):
        
        return self._ObeysBandwidth()
        
    
    def OverrideBandwidth( self, delay = None ):
        
        with self._lock:
            
            if delay is None:
                
                self._bandwidth_manual_override = True
                
                self._wake_time = 0
                
            else:
                
                self._bandwidth_manual_override_delayed_timestamp = HydrusData.GetNow() + delay
                
                self._wake_time = min( self._wake_time, self._bandwidth_manual_override_delayed_timestamp + 1 )
                
            
        
    
    def SetError( self, e, error ):
        
        with self._lock:
            
            self._SetError( e, error )
            
        
    
    def SetFiles( self, files ):
        
        with self._lock:
            
            self._files = files
            
        
    
    def SetFileImportOptions( self, file_import_options ):
        
        with self._lock:
            
            self._file_import_options = file_import_options
            
        
    
    def SetForLogin( self, for_login ):
        
        with self._lock:
            
            self._for_login = for_login
            
        
    
    def SetStatus( self, text ):
        
        with self._lock:
            
            self._status_text = text
            
        
    
    def Sleep( self, seconds ):
        
        with self._lock:
            
            self._Sleep( seconds )
            
        
    
    def Start( self ):
        
        try:
            
            request_completed = False
            
            while not request_completed:
                
                try:
                    
                    response = self._SendRequestAndGetResponse()
                    
                    with self._lock:
                        
                        if self._body is not None:
                            
                            self._ReportDataUsed( len( self._body ) )
                            
                        
                    
                    if 'Content-Type' in response.headers:
                        
                        self._content_type = response.headers[ 'Content-Type' ]
                        
                    
                    if response.ok:
                        
                        with self._lock:
                            
                            self._status_text = u'downloading\u2026'
                            
                        
                        if self._temp_path is None:
                            
                            self._ReadResponse( response, self._stream_io, 104857600 )
                            
                        else:
                            
                            with open( self._temp_path, 'wb' ) as f:
                                
                                self._ReadResponse( response, f )
                                
                            
                        
                        with self._lock:
                            
                            self._status_text = 'done!'
                            
                        
                    else:
                        
                        with self._lock:
                            
                            self._status_text = str( response.status_code ) + ' - ' + str( response.reason )
                            
                        
                        self._ReadResponse( response, self._stream_io, 104857600 )
                        
                        with self._lock:
                            
                            self._stream_io.seek( 0 )
                            
                            data = self._stream_io.read()
                            
                            ( e, error_text ) = ConvertStatusCodeAndDataIntoExceptionInfo( response.status_code, data, self.IS_HYDRUS_SERVICE )
                            
                            self._SetError( e, error_text )
                            
                        
                    
                    request_completed = True
                    
                except HydrusExceptions.ShouldReattemptNetworkException as e:
                    
                    self._current_connection_attempt_number += 1
                    
                    if not self._CanReattemptRequest():
                        
                        raise HydrusExceptions.NetworkException( 'Ran out of reattempts on this error: ' + HydrusData.ToUnicode( e ) )
                        
                    
                    with self._lock:
                        
                        self._status_text = HydrusData.ToUnicode( e ) + '--retrying'
                        
                    
                    time.sleep( 3 )
                    
                except requests.exceptions.ChunkedEncodingError:
                    
                    self._current_connection_attempt_number += 1
                    
                    if not self._CanReattemptRequest():
                        
                        raise HydrusExceptions.ConnectionException( 'Unable to complete request--it broke mid-way!' )
                        
                    
                    with self._lock:
                        
                        self._status_text = u'connection broke mid-request--retrying'
                        
                    
                    time.sleep( 3 )
                    
                except ( requests.exceptions.ConnectionError, requests.exceptions.ConnectTimeout ):
                    
                    self._current_connection_attempt_number += 1
                    
                    if not self._CanReattemptConnection():
                        
                        raise HydrusExceptions.ConnectionException( 'Could not connect!' )
                        
                    
                    with self._lock:
                        
                        self._status_text = u'connection failed--retrying'
                        
                    
                    time.sleep( 3 )
                    
                except requests.exceptions.ReadTimeout:
                    
                    self._current_connection_attempt_number += 1
                    
                    if not self._CanReattemptRequest():
                        
                        raise HydrusExceptions.ConnectionException( 'Connection successful, but reading response timed out!' )
                        
                    
                    with self._lock:
                        
                        self._status_text = u'read timed out--retrying'
                        
                    
                    time.sleep( 3 )
                    
                
            
        except Exception as e:
            
            with self._lock:
                
                self._status_text = 'unexpected error!'
                
                trace = traceback.format_exc()
                
                HydrusData.Print( trace )
                
                self._SetError( e, trace )
                
            
        finally:
            
            with self._lock:
                
                self._SetDone()
                
            
        
    
    def WaitUntilDone( self ):
        
        while True:
            
            self._is_done_event.wait( 5 )
            
            if self.IsDone():
                
                break
                
            
        
        with self._lock:
            
            if self.engine.controller.ModelIsShutdown():
                
                raise HydrusExceptions.ShutdownException()
                
            elif self._error_exception is not None:
                
                if isinstance( self._error_exception, Exception ):
                    
                    raise self._error_exception
                    
                else:
                    
                    raise Exception( 'Problem in network error handling.' )
                    
                
            elif self._IsCancelled():
                
                if self._method == 'POST':
                    
                    message = 'Upload cancelled!'
                    
                else:
                    
                    message = 'Download cancelled!'
                    
                
                raise HydrusExceptions.CancelledException( message )
                
            
        
    
class NetworkJobDownloader( NetworkJob ):
    
    def __init__( self, downloader_page_key, method, url, body = None, referral_url = None, temp_path = None ):
        
        self._downloader_page_key = downloader_page_key
        
        NetworkJob.__init__( self, method, url, body = body, referral_url = referral_url, temp_path = temp_path )
        
    
    def _GenerateNetworkContexts( self ):
        
        network_contexts = NetworkJob._GenerateNetworkContexts( self )
        
        network_contexts.append( ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_DOWNLOADER_PAGE, self._downloader_page_key ) )
        
        return network_contexts
        
    
class NetworkJobSubscription( NetworkJob ):
    
    def __init__( self, subscription_key, method, url, body = None, referral_url = None, temp_path = None ):
        
        self._subscription_key = subscription_key
        
        NetworkJob.__init__( self, method, url, body = body, referral_url = referral_url, temp_path = temp_path )
        
    
    def _GenerateNetworkContexts( self ):
        
        network_contexts = NetworkJob._GenerateNetworkContexts( self )
        
        network_contexts.append( ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_SUBSCRIPTION, self._subscription_key ) )
        
        return network_contexts
        
    
class NetworkJobHydrus( NetworkJob ):
    
    IS_HYDRUS_SERVICE = True
    
    def __init__( self, service_key, method, url, body = None, referral_url = None, temp_path = None ):
        
        self._service_key = service_key
        
        NetworkJob.__init__( self, method, url, body = body, referral_url = referral_url, temp_path = temp_path )
        
    
    def _CheckHydrusVersion( self, service_type, response ):
        
        service_string = HC.service_string_lookup[ service_type ]
        
        headers = response.headers
        
        if 'server' not in headers or service_string not in headers[ 'server' ]:
            
            raise HydrusExceptions.WrongServiceTypeException( 'Target was not a ' + service_string + '!' )
            
        
        server_header = headers[ 'server' ]
        
        ( service_string_gumpf, network_version ) = server_header.split( '/' )
        
        network_version = int( network_version )
        
        if network_version != HC.NETWORK_VERSION:
            
            if network_version > HC.NETWORK_VERSION:
                
                message = 'Your client is out of date; please download the latest release.'
                
            else:
                
                message = 'The server is out of date; please ask its admin to update to the latest release.'
                
            
            raise HydrusExceptions.NetworkVersionException( 'Network version mismatch! The server\'s network version was ' + str( network_version ) + ', whereas your client\'s is ' + str( HC.NETWORK_VERSION ) + '! ' + message )
            
        
    
    def _GenerateNetworkContexts( self ):
        
        network_contexts = []
        
        network_contexts.append( ClientNetworkingContexts.GLOBAL_NETWORK_CONTEXT )
        network_contexts.append( ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_HYDRUS, self._service_key ) )
        
        return network_contexts
        
    
    def _GenerateSpecificNetworkContexts( self ):
        
        # we store cookies on and login to the same hydrus-specific context
        
        session_network_context = ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_HYDRUS, self._service_key )
        login_network_context = session_network_context
        
        return ( session_network_context, login_network_context )
        
    
    def _ReportDataUsed( self, num_bytes ):
        
        service = self.engine.controller.services_manager.GetService( self._service_key )
        
        service_type = service.GetServiceType()
        
        if service_type in HC.RESTRICTED_SERVICES:
            
            account = service.GetAccount()
            
            account.ReportDataUsed( num_bytes )
            
        
        NetworkJob._ReportDataUsed( self, num_bytes )
        
    
    def _SendRequestAndGetResponse( self ):
        
        service = self.engine.controller.services_manager.GetService( self._service_key )
        
        service_type = service.GetServiceType()
        
        if service_type in HC.RESTRICTED_SERVICES:
            
            account = service.GetAccount()
            
            account.ReportRequestUsed()
            
        
        response = NetworkJob._SendRequestAndGetResponse( self )
        
        if service_type in HC.RESTRICTED_SERVICES:
            
            self._CheckHydrusVersion( service_type, response )
            
        
        return response
        
    
class NetworkJobWatcherPage( NetworkJob ):
    
    def __init__( self, watcher_key, method, url, body = None, referral_url = None, temp_path = None ):
        
        self._watcher_key = watcher_key
        
        NetworkJob.__init__( self, method, url, body = body, referral_url = referral_url, temp_path = temp_path )
        
    
    def _GenerateNetworkContexts( self ):
        
        network_contexts = NetworkJob._GenerateNetworkContexts( self )
        
        network_contexts.append( ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_WATCHER_PAGE, self._watcher_key ) )
        
        return network_contexts
        
    
