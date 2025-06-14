# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# NO CHECKED-IN PROTOBUF GENCODE
# source: auth/auth.proto
# Protobuf Python Version: 6.30.0
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_runtime_version.ValidateProtobufRuntimeVersion(
    _runtime_version.Domain.PUBLIC,
    6,
    30,
    0,
    '',
    'auth/auth.proto'
)
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x0f\x61uth/auth.proto\x12\x04\x61uth\"\x8e\x01\n\x0c\x42\x61seResponse\x12\x0e\n\x06status\x18\x01 \x01(\t\x12\x0f\n\x07message\x18\x02 \x01(\t\x12.\n\x06\x64\x65tail\x18\x03 \x03(\x0b\x32\x1e.auth.BaseResponse.DetailEntry\x1a-\n\x0b\x44\x65tailEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12\r\n\x05value\x18\x02 \x01(\t:\x02\x38\x01\"(\n\x12\x43heckAccessRequest\x12\x12\n\njwt_access\x18\x01 \x01(\t\"7\n\x13\x43heckAccessResponse\x12 \n\x04meta\x18\x01 \x01(\x0b\x32\x12.auth.BaseResponse\">\n\x13GetNewTokensRequest\x12\x12\n\njwt_access\x18\x01 \x01(\t\x12\x13\n\x0bjwt_refresh\x18\x02 \x01(\t\"8\n\x14GetNewTokensResponse\x12 \n\x04meta\x18\x01 \x01(\x0b\x32\x12.auth.BaseResponse\"4\n\x0cLoginRequest\x12\x12\n\nuser_email\x18\x01 \x01(\t\x12\x10\n\x08password\x18\x02 \x01(\t\"1\n\rLoginResponse\x12 \n\x04meta\x18\x01 \x01(\x0b\x32\x12.auth.BaseResponse\"8\n\rLogoutRequest\x12\x12\n\njwt_access\x18\x01 \x01(\t\x12\x13\n\x0bjwt_refresh\x18\x02 \x01(\t\"2\n\x0eLogoutResponse\x12 \n\x04meta\x18\x01 \x01(\x0b\x32\x12.auth.BaseResponse\"4\n\x11RegistrateRequest\x12\r\n\x05login\x18\x01 \x01(\t\x12\x10\n\x08password\x18\x02 \x01(\t\"6\n\x12RegistrateResponse\x12 \n\x04meta\x18\x01 \x01(\x0b\x32\x12.auth.BaseResponse\"5\n\x10Verify2faRequest\x12\x0f\n\x07user_id\x18\x01 \x01(\t\x12\x10\n\x08opt_code\x18\x02 \x01(\t\"5\n\x11Verify2faResponse\x12 \n\x04meta\x18\x01 \x01(\x0b\x32\x12.auth.BaseResponse\"+\n\x1bHandleGoogleCallbackRequest\x12\x0c\n\x04\x63ode\x18\x01 \x01(\t\"@\n\x1cHandleGoogleCallbackResponse\x12 \n\x04meta\x18\x01 \x01(\x0b\x32\x12.auth.BaseResponse\"\x19\n\x17GetGoogleAuthUrlRequest\"<\n\x18GetGoogleAuthUrlResponse\x12 \n\x04meta\x18\x01 \x01(\x0b\x32\x12.auth.BaseResponse2\xb6\x04\n\x0b\x41uthService\x12\x42\n\x0b\x43heckAccess\x12\x18.auth.CheckAccessRequest\x1a\x19.auth.CheckAccessResponse\x12\x45\n\x0cGetNewTokens\x12\x19.auth.GetNewTokensRequest\x1a\x1a.auth.GetNewTokensResponse\x12\x30\n\x05Login\x12\x12.auth.LoginRequest\x1a\x13.auth.LoginResponse\x12\x33\n\x06Logout\x12\x13.auth.LogoutRequest\x1a\x14.auth.LogoutResponse\x12?\n\nRegistrate\x12\x17.auth.RegistrateRequest\x1a\x18.auth.RegistrateResponse\x12=\n\nVerify_2fa\x12\x16.auth.Verify2faRequest\x1a\x17.auth.Verify2faResponse\x12_\n\x16Handle_google_callback\x12!.auth.HandleGoogleCallbackRequest\x1a\".auth.HandleGoogleCallbackResponse\x12T\n\x13Get_google_auth_url\x12\x1d.auth.GetGoogleAuthUrlRequest\x1a\x1e.auth.GetGoogleAuthUrlResponseb\x06proto3')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'auth.auth_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
  DESCRIPTOR._loaded_options = None
  _globals['_BASERESPONSE_DETAILENTRY']._loaded_options = None
  _globals['_BASERESPONSE_DETAILENTRY']._serialized_options = b'8\001'
  _globals['_BASERESPONSE']._serialized_start=26
  _globals['_BASERESPONSE']._serialized_end=168
  _globals['_BASERESPONSE_DETAILENTRY']._serialized_start=123
  _globals['_BASERESPONSE_DETAILENTRY']._serialized_end=168
  _globals['_CHECKACCESSREQUEST']._serialized_start=170
  _globals['_CHECKACCESSREQUEST']._serialized_end=210
  _globals['_CHECKACCESSRESPONSE']._serialized_start=212
  _globals['_CHECKACCESSRESPONSE']._serialized_end=267
  _globals['_GETNEWTOKENSREQUEST']._serialized_start=269
  _globals['_GETNEWTOKENSREQUEST']._serialized_end=331
  _globals['_GETNEWTOKENSRESPONSE']._serialized_start=333
  _globals['_GETNEWTOKENSRESPONSE']._serialized_end=389
  _globals['_LOGINREQUEST']._serialized_start=391
  _globals['_LOGINREQUEST']._serialized_end=443
  _globals['_LOGINRESPONSE']._serialized_start=445
  _globals['_LOGINRESPONSE']._serialized_end=494
  _globals['_LOGOUTREQUEST']._serialized_start=496
  _globals['_LOGOUTREQUEST']._serialized_end=552
  _globals['_LOGOUTRESPONSE']._serialized_start=554
  _globals['_LOGOUTRESPONSE']._serialized_end=604
  _globals['_REGISTRATEREQUEST']._serialized_start=606
  _globals['_REGISTRATEREQUEST']._serialized_end=658
  _globals['_REGISTRATERESPONSE']._serialized_start=660
  _globals['_REGISTRATERESPONSE']._serialized_end=714
  _globals['_VERIFY2FAREQUEST']._serialized_start=716
  _globals['_VERIFY2FAREQUEST']._serialized_end=769
  _globals['_VERIFY2FARESPONSE']._serialized_start=771
  _globals['_VERIFY2FARESPONSE']._serialized_end=824
  _globals['_HANDLEGOOGLECALLBACKREQUEST']._serialized_start=826
  _globals['_HANDLEGOOGLECALLBACKREQUEST']._serialized_end=869
  _globals['_HANDLEGOOGLECALLBACKRESPONSE']._serialized_start=871
  _globals['_HANDLEGOOGLECALLBACKRESPONSE']._serialized_end=935
  _globals['_GETGOOGLEAUTHURLREQUEST']._serialized_start=937
  _globals['_GETGOOGLEAUTHURLREQUEST']._serialized_end=962
  _globals['_GETGOOGLEAUTHURLRESPONSE']._serialized_start=964
  _globals['_GETGOOGLEAUTHURLRESPONSE']._serialized_end=1024
  _globals['_AUTHSERVICE']._serialized_start=1027
  _globals['_AUTHSERVICE']._serialized_end=1593
# @@protoc_insertion_point(module_scope)
