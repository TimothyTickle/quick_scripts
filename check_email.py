# https://yuji.wordpress.com/2011/06/22/python-imaplib-imap-example-with-gmail/

import csv
import datetime
import email
import hashlib
import imaplib
#import sciedpiper.commandline
import os


# Conf file constants (keys)
C_STR_EMAIL = "email:"
C_STR_LOCATION = "location:"
C_STR_PASSWORD = "password:"
C_STR_USER = "user:"


##############################################
# Functions
def func_archive( str_message ):
  # Get location to store
  # Store data to location
  # Store email to folder/archive
  # Send email to user

  # Get MD5Sum
  str_md5sum_before = func_get_md5sum( str_from_path )

  # Copy file to data safe
  shutil.copy( src=str_from_path, dst=str_to_path )

  # Get MD5Sum of moved file
  str_md5sum_moved = func_get_md5sum( str_to_path )

  # Check the file move
  if os.path.exists( str_to_path ) and ( str_md5sum_before == str_md5sum_moved ):
    # Move email to another box
    list_ret_copy = mail.uid( 'COPY', str_muid, str_move_folder )
    if list_ret_copy[ 0 ] == "OK":
      mail.uid( 'STORE', str_muid, '+FLAGS', '(|Deleted)' )
      mail.expunge()
    return True
  else:
    return False


def func_get_md5sum( str_file ):
  # Get the md5sum of a file

  hash_cur = haslib.md5()

  with open( str_file, 'rb' ) as str_md5_file:
    buf_cur = str_md5_file.read( C_I_BLOCKSIZE )
    while len( buf_cur ) > 0:
      hash_cur.update( buf_cur )
      buf_cur = str_md5_file.read( C_I_BLOCKSIZE )
  return( hash_cur.hexdigest( ) )


def func_read_conf_file( str_file_path ):
  # Read config file and return as a dict

  dict_return = None
  with open( str_file_path, "r" ) as hndl_conf:
    csvr_cur = csv.reader( hndl_conf, delimiter="\t" )
    dict_return = dict([ [lstr_line[0], lstr_line[1]] for lstr_line in csvr_cur ])
  return( dict_return )


##############################################

# Get account info
str_conf_file = "email_dev.conf"
dict_credentials = func_read_conf_file( str_file_path = str_conf_file ) 

str_account = dict_credentials[ C_STR_USER ]
str_password = dict_credentials[ C_STR_PASSWORD ]

# Mailboxes
str_mail_box = "email_project"
str_done_box = "successfully_archived"

# To archive output folder
str_error_log = "archive.log"

# MD5SUM block size
C_I_BLOCKSIZE = 128

# Search key for email
str_subject_key = "Walkup sequencing GET site information: "

# Key for usr name
str_user_name = "Username: "

# Connect to mail and get inbox
mail = imaplib.IMAP4_SSL("imap.gmail.com")
mail.login( str_account, str_password )
mail.select( str_mail_box )

# Get all the mail and get ids
result, data = mail.uid( "search", None, "(HEADER Subject \""+str_subject_key+"\")" )
for cur_data in data:
  latest_email_uid = cur_data.split()[-1]
  result,data = mail.uid("fetch", latest_email_uid, "(BODY[TEXT])" )
  # Read mail body
  str_message = data[0][1]

  # Get walkup id
  i_walkup_index_start = str_message.find( str_subject_key )
  i_walkup_index_stop = str_message[ i_walkup_index_start:].find( "\r\n" ) + i_walkup_index_start
  str_walkup = str_message[ i_walkup_index_start + len( str_subject_key ) : i_walkup_index_stop ]

  # Get user name
  i_user_name_index_start = str_message.find( str_user_name )
  i_user_name_index_stop = str_message[ i_user_name_index_start:].find( "\r\n" ) + i_user_name_index_start
  str_user_name =  str_message[ i_user_name_index_start + len( str_user_name) : i_user_name_index_stop ]

  print( str_walkup )
  print( str_user_name )

  # If archived successfully then move to another box
  f_success = func_archive( str_message )

  if not f_success:
    # Otherwise log error 
    with open( str_error_log, "a" ) as hndl_error:
      if f_success:
        hndl_error.write( "Failed to archive. Walkup id: " + str_walkup + ", User: " + str_user_name + ", Date: " +  str( datetime.datetime.now() ) + "\n" )
        func_email_success( str_user_name )
      else:
        hndl_error.write( "Successful archive. Walkup id: " + str_walkup + ", User: " + str_user_name + ", Date: " +  str( datetime.datetime.now() ) + "\n" )

# Disconnect
mail.logout()
