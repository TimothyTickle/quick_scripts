# https://yuji.wordpress.com/2011/06/22/python-imaplib-imap-example-with-gmail/

import csv
import datetime
#TODO Do I need this
import email
import hashlib
import imaplib
#import sciedpiper.commandline
import smtplib
import os

# Conf file constants (keys)
C_STR_ADMIN_EMAIL = "admin_email:"
C_STR_BODY_PASSWORD = "Password:"
C_STR_BODY_URL = "URL:"
C_STR_BODY_USERNAME = "Username:"
C_STR_CONFIG_FILE = "email_dev.conf"
C_STR_DONE_BOX = "archive_email_box:"
C_STR_EMAIL = "email:"
C_STR_EMAIL_BODY_DELIMITER = "\r\n"
C_STR_EMAIL_CONTENT = "Content-Type:"
C_STR_EMAIL_TEXT = "text/plain"
C_STR_ERROR_BOX = "Error_email_box:"
C_STR_LOCATION = "location:"
C_STR_LOCK_FILE = "archive.running"
C_STR_LOG_FILE = "archiving.log"
C_STR_MAIL_BOX = "inbox:"
C_STR_OUTBOUND_SMTP_SERVER = "SMTP_Server:"
C_STR_PASSWORD = "password:"
C_STR_PROGRAM_NAME = "Email Archiver v1.0"
C_STR_SUBJECT_KEYWORD = "subject_key:"
C_STR_USER = "user:"
C_STR_USER_NAME_KEYWORD = "user_key:"

# Objects
class IMAPEmail( object ):
  """
  Object that manages all the IMAP email interactions here used for gmail.
  """
  # OK
  def __init__( self, str_mail_box, str_user, str_password ):
    """
    Attempts a connect to the account. If failed, no other functionality will work.
    * str_mail_box : String
                     Email mailbox name
    * str_user : String
                 User name for email login
    * str_password : String
                     Password for email login
    """
    self.f_attached = False
    self.mail = self.func_login( str_login_mail_box=str_mail_box, 
                            str_login_user=str_user, 
                            str_login_password=str_password, 
                            str_login_imap_domain="imap.gmail.com" )
  # OK
  def func_login( self, str_login_mail_box, str_login_user, str_login_password, str_login_imap_domain ):
    """
    Logins into a specific email.
    Any previous email connection is logged out.
    * str_login_mail_box : String
                           Mail box to log into
    * str_login_user : String
                       User name
    * str_login_password : String
                           Password
    * str_login_imap_domain : String
                              The email services' IMAP domain
    * return : Connection to mailbox
    """
    # logout previous
    if self.f_attached:
      self.mail.disconnect()
    # Connect to mail and get inbox
    mail = imaplib.IMAP4_SSL( str_login_imap_domain )
    mail.login( str_login_user, str_login_password )
    self.f_attached = True
    mail.select( str_login_mail_box )
    return mail
  # OK
  def func_get_uid_by_subject_key( self, str_subject_key ):
    """
    Returns uids of mail that match a keyword in their subject.
    str_subject_key : String
                      Subject key to pull mail uids
    return : Returns a tuple result, data or on error None, None
    """
    if self.mail:
      return self.mail.search(  None, "(Subject \""+str_subject_key+"\")" )
    else:
      return None, None
  # OK
  def func_get_email_body_by_uid( self, str_uid ):
    """
    Returns the email body text by UID.
    str_suid : String
               Returns email body buy UID
    return : Returns string email body or empty string on failure
    """
    f_store_text = False
    lstr_return_string = []
    if self.mail:
      typ, msg_data = self.mail.fetch(  str_uid, "(BODY.PEEK[TEXT])" )
      for x_section in msg_data:
        if isinstance( x_section, tuple ):
          for str_line in  x_section[ 1 ].split( C_STR_EMAIL_BODY_DELIMITER ):
            if ( C_STR_EMAIL_CONTENT in str_line ):
              if( C_STR_EMAIL_TEXT in str_line ):
                f_store_text = True
              else:
                f_store_text = False
            if f_store_text:
              lstr_return_string.append( str_line )
      return C_STR_EMAIL_BODY_DELIMITER.join( lstr_return_string )
    else:
      return C_STR_EMAIL_BODY_DELIMITER.join( lstr_return_string )
  # OK
  def func_move_email_to_box( self, str_uid_email, str_old_folder, str_new_folder ):
    """
    Moves an email to a certain box and then deletes the email from the
    original box. Returns a True on success and a False on Failure.
    str_uid_email : uid (string)
                Id identifying an email
    str_old_folder : String
                   : Folder to move email from
    str_new_folder : String
                     Folder to move email to 
    return : Logical (True on success)
    """
    
    if self.mail and not str_uid_email and not str_old_folder and str_new_folder:
      self.mail.select( str_old_folder )
      list_ret_copy = self.mail.copy( str_uid_email, str_new_folder )
      # TODO For some reason I am getting OK if I am in the wrong email box and try to move something. The email does not move but it says it does.
      if list_ret_copy[ 0 ] == "OK":
        self.mail.store( str_uid_email, "+FLAGS", r'(\DELETED)' )
        self.mail.expunge()
        return True
      else:
        return False
    else:
      return False
  # OK
  def func_disconnect( self ):
     """
     Disconnects from current imap connection.
     """
     # Disconnect
     self.mail.logout()
     self.f_attached = False

class EmailArchiver( object ):
  """
  Performs the archiving of samples associated with emails and then moves completed emails to the completed box.
  """
  # Ok
  def __init__( self, str_config_file ):
    """
    Reads in a config file and opens a connection to the email in the config file.
    str_config_file : Str file path
                      Config file that is used to initialize the class.
    """
    # MD5SUM block size
    self.C_I_BLOCKSIZE = 128
    # Parse config file
    self.str_config_file = str_config_file
    self.dict_credentials = self.func_read_conf_file( str_file_path=str_config_file )
    # Open connection to email
    if ( self.dict_credentials and self.dict_credentials.get( C_STR_MAIL_BOX, None ) and 
         self.dict_credentials.get( C_STR_USER, None ) and self.dict_credentials.get( C_STR_PASSWORD, None ) ):
      self.cur_connection = IMAPEmail( str_mail_box=self.dict_credentials.get( C_STR_MAIL_BOX, None ),
                                       str_user=self.dict_credentials.get( C_STR_USER, None ),
                                       str_password=self.dict_credentials.get( C_STR_PASSWORD, None ) )
    else:
      self.cur_connection = None
      self.cur_log_hndl = None
    # Set up logger for the archiving system
    self.logr = logging.getLogger( C_STR_PROGRAM_NAME )

  def func_archive( self, str_uid ):
    """
    Archive data from email account.
    Returns true (not success) and false (no success)

    * str_uid : String
                Id for an email 
    * return : Returns logical (True is successful)
    """

    # Email log file
    str_email_log_file = "_".join( [ self.func_now(), str_uid ] )+".log"

    # Open logger
    with open( str_email_log_file, "w" ) as hndl_mail_logger:

      # Log uid
      hndl_mail_logger.write( self.func_now()+"::check_email::INFO:: Start archiving uid "+str_uid+".\n" )

      # Make sure we have a connection
      if ( not self.cur_connection or not self.dict_credentials.get( C_STR_SUBJECT_KEYWORD, None ) 
           or not self.dict_credentials.get( C_STR_USER_KEYWORD, None ) or not self.dict_credentials.get( C_STR_LOCATION, None ) ):
        # Log to email log
        hndl_mail_logger.write( self.func_now()+"::check_email::ERROR:: Did not read enough info from the config file to make a connection.\n" )
        hndl_mail_logger.write( self.func_now()+"::check_email::ERROR:: Please check config file:"+self.str_config_file+"\n" )
        return False

      # Get email body
      str_message = self.cur_connection.func_get_email_body_by_uid(str_uid)
      hndl_mail_logger.write( self.func_now()+"::check_email::INFO:: Retrieved email body.\n" )

      ## Get MiSEQ credentials
      dict_email_tokens = self.func_parse_email_body( str_message )
      str_url = dict_email_tokens[ C_STR_BODY_URL ]
      str_password = dict_email_tokens[ C_STR_BODY_PASSWORD ]
      str_user_name = dict_email_tokens[ C_STR_BODY_USERNAME ]
      if not str_url or not str_password or not str_user_name:
        str_password_error = "NOT EMPTY" if str_password else "EMPTY"
        hndl_mail_logger.write( self.func_now()+"::check_email::ERROR:: Did not get credentials from walkup sequencing email." )
        hndl_mail_logger.write( self.func_now()+"::check_email::ERROR:: URL="+str_url)
        hndl_mail_logger.write( self.func_now()+"::check_email::ERROR:: USERNAME="+str_user_name)
        hndl_mail_logger.write( self.func_now()+"::check_email::ERROR:: PASSWORD="+str_password_error)

      # Move associated data
      hndl_mail_logger.write( self.func_now()+"::check_email::INFO:: Start moving from "+str_move_from_path+" to "+self.dict_credentials.get( C_STR_LOCATION, None )+"\n" )
      str_copy_dir = func_archive_data( str_move_from_path, self.dict_credentials.get( C_STR_LOCATION, None ) )
      if str_copy_dir:
        hndl_mail_logger.write( self.func_now()+"::check_email::INFO:: Data move was successful. "+str_copy_dir+"\n" )
        f_email_move_success=self.cur_connection.func_move_email_to_box( uid_email=str_uid, str_old_folder=self.dict_credentials.get( C_STR_MAIL_BOX, None), str_new_folder=self.dict_credentials.get( C_STR_DONE_BOX, None ) )
        if f_email_move_success:
          # Log
          hndl_mail_logger.write( self.func_now()+"::check_email::INFO:: Email move was successful.\n" )
        else:
          # Log
          hndl_mail_logger.write( self.func_now()+"::check_email::INFO:: Email move was NOT successful.\n" )
          return f_email_move_success
      else:
        hndl_mail_logger.write( self.func_now()+"::check_email::INFO:: Data move was unsuccessful, notifying admin.\n" )
        self.func_data_fail_alert( str_error_uid=str_uid, str_error_move_path=str_move_from_path, str_original_path=str_move_to_path, str_log=str_email_log_file )
        self.cur_connection.func_move_email_to_box( uid_email=str_uid, str_old_folder=self.dict_credentials.get( C_STR_MAIL_BOX, None), str_new_folder=self.dict_credentials.get( C_STR_ERROR_BOX, None ) )
        return False

      # Write the mail to archive directory
      str_mail_content_file = os.path.join( str_copy_dir, str_uid )+".txt"
      with open( str_mail_content_file, "w" ) as hndl_mail_content:
        hndl_mail_content.write( str_message+"\n" )

    # Copy the email log to the archive
    shutil.mv( isrc=str_email_log_file, dst=str_copy_dir )

    return True

  def func_data_fail_alert( str_error_uid, str_error_move_path, str_original_path, str_message_body, str_log ):
    """
    Sends an email to the admin to alert them a data copy did not complete.

    * str_error_uid : String
                      ID for the email that failed.
    * str_error_move_path : String path
                            Path to where the data was to be placed.
    * str_original_path : String path
                          Path where the data was to be copied from.
    * str_message_body : String
                       : Body of the email
    * str_log : String path
                Path to the log for this failed process.
    """
    # Make email
    mime_message = email.mime.multipart( From=self.dict_credentials[ C_STR_USER ], 
                                         To=self.dict_credentials[ C_STR_ADMIN ], 
                                         Date=email.utils.formatdate(localtime=True),
                                         Subject="ERROR Please help me archive this data." )
    # Add Message
    str_email_message = "\n".join( [ "Attempted to archive email id: "+str_error_uid,
                                     "Archive data from: " + str_original_path,
                                     "Archive data to: " + str_error_move_path,
                                     "Email body:\n" + str_message_body ] )
    # Add email message
    mime_message.attach( email.mime.text( str_email_message ) )
    # Attach log file as an attachment
    with open( str_log, "rb" ) as hndl_log:
      mime_message.attach( email.mime.application( hndl_log.read(), 
                                                   Content_Disposition="attachment; filename="+os.path.basename( str_log ) ) )
    # Email admin
    email_server = smtplib.SMTP( self.dict_credentials[ C_STR_OUTBOUND_SMTP_SERVER ] )
    email_server.sendmail( self.dict_credentials[ C_STR_USER ],
                           self.dict_credentials[ C_STR_ADMIN ],
                           mime_message.as_string() )
    email_server.close()


  def func_archive_data( self, str_move_from_path, str_move_to_path ):
    """
    Archive data from one email.
    Will not write over an existing directory
    MD5Sum is check before and afterwards.

    * str_move_from_path : String path
                           Archive data from this path (dir)
    * str_move_to_path : String path
                         Archive data to this path (dir)
    * return : Logical (True is success) 
    """

    ## TODO Update the move path with the current time
    # Make sure it is unique
    # If not unique (not likely) keep adding a number on to it until it is.
    # Fail after 100 attempts.

    # Get MD5Sum
    str_md5sum_before = self.func_get_md5sum( str_from_path )

    # Copy file to data safe
    shutil.copy( src=str_from_path, dst=str_to_path )

    # Get MD5Sum of moved file
    str_md5sum_moved = self.func_get_md5sum( str_to_path )

    # Check the file move
    # If successful return true but do not delete the old files, they will be deleted as they age out in the directory
    # If not successful, delete file that was moved if it exists.
    if os.path.exists( str_to_path ) and ( str_md5sum_before == str_md5sum_moved ):
      return True
    else:
      if os.path.exists( str_to_path ):
        os.remove( str_to_path )
    return False

  # Checked
  def func_get_md5sum( self, str_file ):
    """
    Get the md5sum of a file

    * str_file : String (path)
                 File to get md5sum
    * return : MD5Sum
    """

    hash_cur = hashlib.md5()

    with open( str_file, 'rb' ) as str_md5_file:
      buf_cur = str_md5_file.read( self.C_I_BLOCKSIZE )
      while len( buf_cur ) > 0:
        hash_cur.update( buf_cur )
        buf_cur = str_md5_file.read( self.C_I_BLOCKSIZE )
    return( hash_cur.hexdigest( ) )

  # ok
  def func_parse_email_body( self, str_email_body ):
    dict_return = {}
    if not str_email_body:
      return dict_return
    for str_line in str_email_body.split( C_STR_EMAIL_BODY_DELIMITER ):
      if C_STR_BODY_URL in str_line:
        dict_return[ C_STR_BODY_URL ] = [ str_token for str_token in str_line.split(" ") if str_token ][1]
        continue
      if C_STR_BODY_USERNAME in str_line:
        dict_return[ C_STR_BODY_USERNAME ] = [ str_token for str_token in str_line.split(" ") if str_token ][1]
        continue
     if C_STR_BODY_PASSWORD in str_line:
         dict_return[ C_STR_BODY_PASSWORD ] = [ str_token for str_token in str_line.split(" ") if str_token ][1]
         continue
    return dict_return

  # Read ok
  def func_get_unarchived_emails( self ):
    """
    Retrieves a list of uids for all email that have not yet been archived.

    * return : List of uids (strings)
    """

    # Make sure that there is a connection
    if not self.cur_connection:
      return None

    # List of uids of unarchived emails
    list_ret_uids = []
    # Get unarchived emails
    result, data = self.cur_connection.func_get_uid_by_subject_key( str_subject_key=str_subject_key )
    if not data:
      return list_ret_uids

    # Get all the mail ids
    for cur_data in data:
      list_ret_uids.append( cur_data.split()[-1] )
    return list_ret_uids
  
  # OK
  def func_read_conf_file( self, str_file_path ):
    """
    Read config file and return as a dict.

    * str_file_path : String path
                      Config file.
    * return : Dict ({ conf_key: conf_value })
    """

    # Dict of config info
    # { conf_key: config_value }
    dict_return = None
    with open( str_file_path, "r" ) as hndl_conf:
      csvr_cur = csv.reader( hndl_conf, delimiter="\t" )
      dict_return = dict([ [ lstr_line[0], lstr_line[1] ] for lstr_line in csvr_cur ])
    return( dict_return )

  # Checked
  def func_now( self ):
    """
    Return formated date and time.

    * return : String formated date and time.
    """

    str_stamp = datetime.datetime.isoformat( datetime.datetime.now())
    for str_token in [":",".","-"]:
      str_stamp = str_stamp.replace( str_token, "_" )
    return str_stamp

  # Read ok
  def func_disconnect( self ):
    """
    Disconnect from the email account and close connection.
    """

    if self.cur_connection:
      self.cur_connection.func_disconnect()
    self.cur_connection = None


  ###### Lock related functions
  # These are used to make sure only one process is runing at a time.
  # This is needed incase there are a lot of files to process and they take more
  # more time than is given between cron job instatiations of this program.
  # In that case we would have two processes running on the same data at one time
  # and the state of the archiving would not be reliable.
  ######
  # checked
  def func_lock( self ):
    """
    Lock the archiving system so another archive process can not be ran.
    """
    with open( self.C_STR_LOCK_FILE, "w" ) as hndl_lock:
      hndl_lock.write( self.func_now() )

  # Checked
  def func_unlock( self ):
    """
    Unlock the archiving system so other processes can be ran.
    """
    if os.path.exists( self.C_STR_LOCK_FILE ):
      os.remove( self.C_STR_LOCK_FILE )

  # checked
  def func_is_locked( self ):
    """
    Check to see if the archiving system is locked by antoehr process.

    * return : Logical (True = success)
    """
    return os.path.exists( self.C_STR_LOCK_FILE )


##############################################
# Start script
##############################################

#with open( C_STR_LOG_FILE, "a" ) as hndl_archive_log:

# Create EmailArchiver
arch_system = EmailArchiver( str_config_file=C_STR_CONFIG_FILE )

#  # Check if the system is locked.
#  ## If the system is locked, log, and return an error
#  if arch_system.func_is_locked():
#    # Log The system is locked and return
#    ## LOG TODO
#    exit( 101 )

#  # Lock the system if it was not locked
#  arch_system.func_lock()

#  # Get new emails
#  list_uid = EmailArchiver.func_get_unarchived_emails()

#  # Attempt to archive each new email
#  for cur_uid in list_uid:
#    f_success = EmailArchiver.func_archive( list_uid )
#    # Log ##TODO

#    ## TODO Run make samples.txt

    # Email user

#  # Unlock archiving system for later use.
#  arch_system.func_unlock()

#  # Disconnect
arch_system.func_disconnect()
