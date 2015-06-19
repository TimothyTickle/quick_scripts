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
C_STR_CONFIG_FILE = "email_dev.conf"
C_STR_DONE_BOX = "archive_email_box:"
C_STR_EMAIL = "email:"
C_STR_ERROR_BOX = "Error_email_box:"
C_STR_LOCATION = "location:"
C_STR_LOCK_FILE = "archive.running"
C_STR_LOG_FILE = "archiving.log"
C_STR_MAIL_BOX = "inbox:"
C_STR_OUTBOUND_SMTP_SERVER = "SMTP_Server:"
C_STR_PASSWORD = "password:"
C_STR_SUBJECT_KEYWORD = "subject_key:"
C_STR_USER = "user:"
C_STR_USER_NAME_KEYWORD = "user_key:"

# Objects
class IMAPEmail( object ):
  """
  Object that manages all the IMAP email interactions here used for gmail.
  """

  def __init__( self, str_mail_box, str_user, str_password ):
    """
    Attempts a connect to the account. If not no other functionality will work.

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
    self.f_attached = True

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
      self.f_attached = False
    
    # Connect to mail and get inbox
    mail = imaplib.IMAP4_SSL( str_login_imap_domain )
    mail.login( str_login_user, str_login_password )
    mail.select( str_login_mail_box )
    return mail

  def func_get_uid_by_subject_key( self, str_subject_key ):
    """
    Returns uids of mail that match a keyword in their subject.

    str_subject_key : String
                      Subject key to pull mail uids
    return : Returns a tuple result, data or on error None, None
    """

    if self.mail:
      return self.mail.uid( "search", None, "(HEADER Subject \""+str_subject_key+"\")" )
    else:
      return None, None

  def func_move_email_to_box( self, uid_email, str_new_folder ):
    """
    Moves an email to a certain box and then deletes the email from the
    original box. Returns a True on success and a False on Failure.

    uid_email : uid (string)
                Id identifying an email
    str_new_folder : String
                     Folder to move email to 
    return : Logical (True on success)
    """
    if self.mail:
      list_ret_copy = self.mail.uid( 'COPY', str_muid, str_new_folder )
      if list_ret_copy[ 0 ] == "OK":
        self. mail.uid( 'STORE', str_muid, '+FLAGS', '(|Deleted)' )
        self.mail.expunge()
        return True
      else:
        return False
    else:
      return False

  def func_disconnect( self ):
     """
     Disconnects from current imap connection.
     """

     # Disconnect
     self.mail.logout()


class EmailArchiver( object ):
  """
  Performs the archiving of samples associated with emails and then moves completed emails to the completed box.
  """

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
      result, data = self.cur_connection.uid("fetch", str_uid, "(BODY[TEXT])" )
      hndl_mail_logger.write( self.func_now()+"::check_email::INFO:: Retrieved email body.\n" )
      # TODO check result

      # parse email body for info
      str_message = data[0][1]
      ## Get walkup id
      i_walkup_index_start = str_message.find( self.dict_credentials.get( C_STR_SUBJECT_KEYWORD, None ) )
      i_walkup_index_stop = str_message[ i_walkup_index_start:].find( "\r\n" ) + i_walkup_index_start
      str_walkup = str_message[ i_walkup_index_start + len( self.dict_credentials.get( C_STR_SUBJECT_KEYWORD, None ) ) : i_walkup_index_stop ]
      ## Get user name
      i_user_name_index_start = str_message.find( self.dict_credentials.get( C_STR_USER_KEYWORD, None ) )
      i_user_name_index_stop = str_message[ i_user_name_index_start:].find( "\r\n" ) + i_user_name_index_start
      str_user_name =  str_message[ i_user_name_index_start + len( self.dict_credentials.get( C_STR_USER_KEYWORD, None )  ) : i_user_name_index_stop ]
      ## Get DATA TODO
      # str_move_from_path =

      # Move associated data
      hndl_mail_logger.write( self.func_now()+"::check_email::INFO:: Start moving from "+str_move_from_path+" to "+self.dict_credentials.get( C_STR_LOCATION, None )+"\n" )
      str_copy_dir = func_archive_data( str_move_from_path, self.dict_credentials.get( C_STR_LOCATION, None ) )
      if str_copy_dir:
        hndl_mail_logger.write( self.func_now()+"::check_email::INFO:: Data move was successful. "+str_copy_dir+"\n" )
        f_email_move_success=self.cur_connection.func_move_email_to_box( uid_email=str_uid, str_new_folder=self.dict_credentials.get( C_STR_DONE_BOX, None ) )
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
        self.cur_connection.func_move_email_to_box( uid_email=str_uid, str_new_folder=self.dict_credentials.get( C_STR_ERROR_BOX, None ) )
        return False

      # Write the mail to archive directory
      str_mail_content_file = os.path.join( str_copy_dir, str_uid )+".txt"
      with open( str_mail_content_file, "w" ) as hndl_mail_content:
        hndl_mail_content.write( str_message+"\n" )

    # Copy the log to the archive
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
                                     "Archive data from: "+
                                     "Archive data to: "+
                                     "Email body:",
                                     str_meail_body ] )
    # Add email message
    mime_message.attach( email.mime.text( str_message_body ) )
    # Attach log file
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
    if os.path.exists( str_to_path ) and ( str_md5sum_before == str_md5sum_moved ):
      # shutil.rm( str_from_path )
      return True
    return False

  def func_get_md5sum( self, str_file ):
    """
    Get the md5sum of a file

    * str_file : String (path)
                 File to get md5sum
    * return : MD5Sum
    """

    hash_cur = haslib.md5()

    with open( str_file, 'rb' ) as str_md5_file:
      buf_cur = str_md5_file.read( self.C_I_BLOCKSIZE )
      while len( buf_cur ) > 0:
        hash_cur.update( buf_cur )
        buf_cur = str_md5_file.read( self.C_I_BLOCKSIZE )
    return( hash_cur.hexdigest( ) )

  def func_get_unarchived_emails( self ):
    """
    Retrieves a list of uids for all email that have not yet been archived.

    * return : List of uids (strings)
    """

    # List of uids of unarchived emails
    list_ret_uids = []
    # Get unarchived emails
    result, data = cur_connection.func_get_uid_by_subject_key( str_subject_key=str_subject_key )
    # TODO Check result

    # Get all the mail ids
    for cur_data in data:
      list_ret_uids.append( cur_data.split()[-1] )
    return list_ret_uids
  
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

  def func_now( self ):
    """
    Return formated date and time.

    * return : String formated date and time.
    """

    return [ datetime.datetime.isoformat( datetime.datetime.now()).replace( str_token,"_" ) for str_token in [":",".","-"] ]

  def func_disconnect( self ):
    """
    Disconnect from the email account and close connection.
    """

    if self.cur_connection:
      self.cur_disconnect()
    self.cur_connection = None

  ###### Lock related functions
  def func_lock( self ):
    """
    Lock the archiving system so another archive process can not be ran.
    """

    with open( self.C_STR_LOCK_FILE, "w" ) as hndl_lock:
      hndl_lock.write( date.time.now() )

  def func_unlock( self ):
    """
    Unlock the archiving system so other processes can be ran.
    """

    shutil.rm( self.C_STR_LOCK_FILE )

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

#  # Unlock archiving system for later use.
#  arch_system.func_unlock()

#  # Disconnect
arch_system.func_disconnect()
