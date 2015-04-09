# https://yuji.wordpress.com/2011/06/22/python-imaplib-imap-example-with-gmail/

import datetime
import email
import imaplib
import os

# Account information, so very bad 
str_account = ""
str_password = ""

# Mailboxes
str_mail_box = "email_project"
Str_done_box = "successfully_archived"

# Sucessful archive file
str_archive_file = "archive.txt"

# To archive output folder
str_error_log = "archive_errors.txt"

# Search key for email
str_subject_key = "Walkup sequencing GET site information: "

# Key for usr name
str_user_name = "Username: "

def func_archive( str_message ):
  # Get location to store
  # Store data to location
  # Store email to folder/archive
  # Send email to user

  # Move email to another box
  list_ret_copy = mail.uid( 'COPY', str_muid, str_move_folder )
  if list_ret_copy[ 0 ] == "OK":
    mail.uid( 'STORE', str_muid, '+FLAGS', '(|Deleted)' )
    mail.expunge()
  return False

# Connect to mail and get inbox
mail = imaplib.IMAP4_SSL("imap.gmail.com")
mail.login( str_account, str_password )
mail.select( str_mail_box )

# Read previously archived files
# { Walkup id : username }
dict_known_files = {}
if os.path.exists( str_archive_file ):
  with open( str_archive_file ) as hndl_archive:
    dict_known_files = dict( hndl_archive.read() )

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
      hndl_error.write( "Failed to archive. Walkup id: " + str_walkup + ", User: " + str_user_name + ", Date: " +  str( datetime.datetime.now() ) + "\n" )

# Disconnect
mail.logout()
