#################################################################################
#
# Copyright (c) 2013 Genome Research Ltd.
# 
# Author: Irina Colgiu <ic4@sanger.ac.uk>
# 
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 3 of the License, or (at your option) any later
# version.
# 
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.
# 
# You should have received a copy of the GNU General Public License along with
# this program. If not, see <http://www.gnu.org/licenses/>.
# 
#################################################################################


from django.views.generic import TemplateView
from django.views.generic.edit import FormView
from django.http import HttpResponseRedirect

#from serapis.forms import UploadForm
from serapis.controller.frontend import validator, controller
from serapis import serializers
from serapis.com import utils
from serapis.controller.db import models
from serapis.controller import exceptions
from serapis.controller.logic import controller_strategy

from voluptuous import MultipleInvalid
#from django.http import HttpResponse
from rest_framework.renderers import JSONRenderer
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView
#from rest_framework.decorators import api_view

#from rest_framework.routers import *

#from serializers import ObjectIdEncoder

from os import listdir
from os.path import isfile, join
from bson.objectid import ObjectId
from pymongo.errors import InvalidId

#import ipdb
import errno
import json
from mongoengine.queryset import DoesNotExist
from mongoengine.errors import NotUniqueError
#from celery.bin.celery import result

import logging
logging.basicConfig(level=logging.DEBUG)

    
USER_ID = 'ic4'
        

# ----------------------------- AUXILIARY FCTIONS ---------------------------

def _decode_list(data):
    rv = []
    for item in data:
        if isinstance(item, unicode):
            item = item.encode('utf-8')
        elif isinstance(item, list):
            item = _decode_list(item)
        elif isinstance(item, dict):
            item = _decode_dict(item)
        rv.append(item)
    return rv

def _decode_dict(data):
    rv = {}
    for key, value in data.iteritems():
        if isinstance(key, unicode):
            key = key.encode('utf-8')
        if isinstance(value, unicode):
            value = value.encode('utf-8')
        elif isinstance(value, list):
            value = _decode_list(value)
        elif isinstance(value, dict):
            value = _decode_dict(value)
        rv[key] = value
    return rv

#obj = json.loads(s, object_hook=_decode_dict)

        
#----------------------------- AUXILIARY TEMPORARY --------------------------
def replace_null_id_json(file_submitted):
    if 'null' in file_submitted:
        file_submitted['null'] = '_id'
        
#def from_unicode_to_string(data):
#    new_data = dict()
#    for elem in data:
#        key = ''.join(chr(ord(c)) for c in elem)
#        val = ''.join(chr(ord(c)) for c in data[elem])
#        new_data[key] = val
#    return new_data
#            
#
#def from_unicode_to_string(input):
#    if isinstance(input, dict):
#        return dict((from_unicode_to_string(key), from_unicode_to_string(value)) for key, value in input.iteritems())
#    elif isinstance(input, list):
#        return [from_unicode_to_string(element) for element in input]
#    elif isinstance(input, unicode):
#        return input.encode('utf-8')
#    else:
#        return input


# ----------------------- REFERENCE GENOMES HANDLING --------------------

#/references
class ReferencesMainPageRequestHandler(APIView):
    
    def get(self, request, format=None):
        context = controller_strategy.GeneralReferenceGenomeContext()
        strategy = controller_strategy.ReferenceGenomeRetrivalStrategy()
        references = strategy.process_request(context)
        serial_refs = serializers.serialize(references)
        return Response({"result" : serial_refs}, status=200)
    
    def post(self, request, format=None):
        if not hasattr(request, 'DATA'):
            return Response(status=304)
        try:
            context = controller_strategy.GeneralReferenceGenomeContext(request.DATA)
            strategy = controller_strategy.ReferenceGenomeInsertionStrategy()
            ref_id = strategy.process_request(context)
            return Response({"result" : ref_id}, status=201)
        except NotUniqueError:
            return Response("Resource already exists", status=424)
    
    
    
# /references/123/
class ReferenceRequestHandler(APIView):
    
    def get(self, request, reference_id):
        print "RENDERERS -- default : ", self.renderer_classes
        context = controller_strategy.ReferenceGenomeContext(reference_id)
        strategy = controller_strategy.ReferenceGenomeRetrivalStrategy()
        ref = strategy.process_request(context)
        return Response({"result" : serializers.serialize(ref)})
    
    # Should we really allow the users to modify references? Maybe if they are admins...
    def put(self, request, reference_id, format=None):
        if not hasattr(request, 'DATA'):
            return Response("No data to be updated", 304)
        context = controller_strategy.ReferenceGenomeContext(reference_id, request.DATA)
        strategy = controller_strategy.ReferenceGenomeModificationStrategy()
        updated = strategy.process_request(context)
        return Response({"result" : serializers.serialize(updated)})
    

# ----------------------- GET MORE SUBMISSIONS OR CREATE A NEW ONE-------

# /submissions/
class SubmissionsMainPageRequestHandler(APIView):
    # GET all the submissions for a user_id
    def get(self, request, format=None):
        ''' Retrieves all the submissions for this user. '''
        user_id = USER_ID
        context = controller_strategy.GeneralSubmissionContext(user_id)
        strategy = controller_strategy.SubmissionRetrievalStrategy()
        submission_list = strategy.process_request(context)
        submission_list = serializers.serialize(submission_list)
        return Response(submission_list, status=200)


#        submissions_list = controller.get_all_submissions(user_id)
#        subm_serialized = serializers.serialize(submissions_list)
#        return Response("Submission list: "+subm_serialized, status=200)
    
    
    # POST = create a new submission, for uploading the list of files given as param
    def post(self, request):
        ''' Creates a new submission, given a set of files.
            No submission is created if the list of files is empty.
            Returns:
                - status=201 if the submission is created
                - status=400 if the submission wasn't created (list of files empty).
        '''
        user_id = USER_ID
        try:
#            data = request.POST['_content']
            print "start of the reqest!!!!"
            req_result = dict()
#            data = request.DATA
#            data = utils.unicode2string(data)
#            #validator.submission_schema(data)       # throws MultipleInvalid exc if Bad Formed Req.
#            validator.submission_post_validator(data)
            
            import time #, ipdb
            t1 = time.time()
#            subm_result = controller.create_submission(user_id, data)
            context = controller_strategy.GeneralContext(user_id, request_data=request.DATA)
            subm_result = controller_strategy.SubmissionCreationStrategy.process_request(context)
            
            t2 = time.time() - t1
            print "TIME TAKEN TO RUN create_subm: ", t2 
            submission_id = subm_result.result
            print "SUBMISSION RESULT: ", vars(subm_result)
            if subm_result.error_dict:
                req_result['errors'] = subm_result.error_dict
            if not submission_id:
                req_result['message'] = "Submission not created."
                if subm_result.message:
                    req_result['message'] = req_result['message'] + subm_result.message
                if subm_result.warning_dict:
                    req_result['warnings'] = subm_result.warning_dict
                return Response(req_result, status=424)
            else:
                msg = "Submission created" 
                req_result['message'] = msg
                req_result['result'] = submission_id 
                if subm_result.warning_dict:
                    req_result['warnings'] = subm_result.warning_dict
                # TESTING PURPOSES:
                #files = [str(f.id) for f in db_model_operations.retrieve_all_files_from_submission(result_dict['submission_id'])]
                files = [str(f.id) for f in models.SubmittedFile.objects(submission_id=submission_id).all()]
                req_result['testing'] = files
                # END TESTING
                return Response(req_result, status=201)
        except MultipleInvalid as e:
            path = ''
            for p in e.path:
                if path:
                    path = path+ '->' + str(p)
                else:
                    path = str(p)
            print "TYPE: ", type(e)
            print " and e: ", str(e)
            #req_result['error'] = "Message contents invalid: "+e.message + " "+ path
            req_result['error'] = str(e)
            return Response(req_result, status=400)
        except exceptions.NotEnoughInformationProvided as e:
            req_result['error'] = e.strerror
            logging.error("Not enough info %s", e)
            logging.error(e.strerror)
            return Response(req_result, status=424)
        except exceptions.InformationConflict as e:
            req_result['error'] = e.strerror
            logging.error("Information conflict %s", e)
            logging.error(e.strerror)
            return Response(req_result, status=424)
        except ValueError as e:
            logging.error("Value error %s", e.message)
            req_result['error'] = e.message
            return Response(req_result, status=424)
        except exceptions.ResourceNotFoundError as e:
            logging.error("Resource not found: %s", e.faulty_expression)
            return Response(e.message, status=400)
        except exceptions.InvalidRequestData as e:
            logging.error("Invalid request data on POST request to submissions.")
            result = {'errors' : e.faulty_expression, 'message' : e.message}
            return Response(result, status=400)
            
        #This should be here: 
#        except:
#            return Response("Unexpected error:"+ str(sys.exc_info()[0]), status=400)
    
    
    
# ---------------------- HANDLE 1 SUBMISSION -------------

# /submissions/submission_id
class SubmissionRequestHandler(APIView):
    def get(self, request, submission_id, format=None):
        ''' Retrieves a submission given by submission_id.'''
        try:
            user_id = USER_ID
            result = dict()
            logging.debug("Received GET request - submission id:"+submission_id)
            #submission = controller.get_submission(submission_id)
            context = controller_strategy.SpecificSubmissionContext(user_id, submission_id)
            strategy = controller_strategy.SubmissionRetrievalStrategy()
            submission = strategy.process_request(context)
            submission_serial = serializers.serialize(submission)
        except InvalidId:
            result['errors'] = "Invalid id"
            return Response(result, status=404)
        except DoesNotExist:
            result['errors'] = "Submission does not exist"
            return Response(result, status=404)
        else:
            #subm_serialized = serializers.serialize(submission)
            result['result'] = submission_serial
            return Response(result, status=200)
        
# Given the fact that submission is not an entity itself, there is nothing to be updated about it.
# It's only purpose is to keep track of a bunch of files that people wish to submit at the same time.
# The only important fiels are - status - which is only modifiable by the application itself and files_list.
# Hence one can either delete a file from that submission or add a new one, otherwise there's nothing else 
# one can do to that list...
#    def put(self, request, submission_id, format=None):
#        ''' Updates a submission with the data provided on the POST request.'''
#        try:
#            data = request.DATA
# ...



    def delete(self, request, submission_id):
        ''' Deletes the submission given by submission_id. '''
        try:
            result = dict()
            was_deleted = controller.delete_submission(submission_id)
        except InvalidId:
            result['errors'] = "InvalidId"
            return Response(result, status=404)
        except DoesNotExist:
            result['errors'] = "Submission does not exist"
            return Response(result, status=404)
        else:
            if was_deleted:
                result['result'] = "Submission successfully deleted."
                return Response(result, status=200)
            else:
                result['result'] = "Submission not deleted - probably because the files have been already submitted to iRODS"
                return Response(result, status=424)   # Method failed OR 304 - Not modified (but this is more of an UPDATE status response
                
            #TODO: here there MUST be treated also the other exceptions => nothing will happen if the app throws other type of exception,
            # it will just prin OTHER EXCEPTIOn - on that branch
        

# /submissions/submission_id/status/
class SubmissionStatusRequestHandler(APIView):
    def get(self, request, submission_id, format=None):
        ''' Retrieves the status of the submission. '''
        try:
            result = dict()
            subm_statuses = controller.get_submission_status(submission_id)
        except InvalidId:
            result['errors'] = "InvalidId"
            return Response(result, status=404)
        except DoesNotExist:
            result['errors'] = "Submission not found"
            return Response(result, status=404)
        else:
            result['result'] = subm_statuses
            return Response(result, status=200)


class AllSubmittedFilesStatusesHandler(APIView):
    def get(self, request, submission_id, format=None):
        ''' Retrieves the status of all files in this submission. '''
        try:
            result = dict()
            subm_statuses = controller.get_all_submitted_files_status(submission_id)
        except InvalidId:
            result['errors'] = "InvalidId"
            return Response(result, status=404)
        except DoesNotExist:
            result['errors'] = "Submission not found"
            return Response(result, status=404)
        else:
            result['result'] = subm_statuses
            return Response(result, status=200)
    
          

#---------------- HANDLE 1 SUBMITTED FILE ------------------------

#------------------ STATUS----------------------------------------

# /submissions/submission_id/123/files/1/status
class SubmittedFileStatusRequestHandler(APIView):
    def get(self, request, submission_id, file_id, format=None):
        ''' Retrieves the statuses of the submitted file (upload and mdata). 
        '''
        try:
            result = dict()
            subm_statuses = controller.get_submitted_file_status(file_id)
        except InvalidId:
            result['errors'] = "InvalidId"
            return Response(result, status=404)
        except DoesNotExist:
            result['errors'] = "Submitted file not found"
            return Response(result, status=404)
        else:
            result['result'] = subm_statuses
            return Response(result, status=200)

 

#----------------- HANDLE 1 SUBMITTED FILE REQUESTS ---------------
        

# URL: /submissions/123/files/
class SubmittedFilesMainPageRequestHandler(APIView):
    ''' Handles the requests coming for /submissions/123/files/.
        GET - retrieves the list of files for this submission.
        POST - adds a new file to this submission.'''
    def get(self, request, submission_id, format=None):
        try:
            result = dict()
            context = controller_strategy.GeneralFileContext(USER_ID, submission_id)
            strategy = controller_strategy.FileRetrievalStrategy()
            files = strategy.process_request(context)
        except InvalidId:
            result['errors'] = "Invalid id"
            return Response(result, status=404)
        except DoesNotExist:
            result['errors'] = "Submission not found"
            return Response(result, status=404)
        else:
            #file_serial = serializers.serialize(files)
            #result['result'] = file_serial
            files_serial = serializers.serialize(files)
            result['result'] = files_serial
            #result_serial = serializers.serialize_excluding_meta(result)
            logging.info("Submitted files list: "+files_serial)
            return Response(files_serial, status=200)
        
        
    # TODO: should I really expose this method?
    def post(self, request, submission_id, format=None):
        ''' Resubmit jobs for each file of this submission - used in case of permission denied
            or other errors that may have happened during the submission (DB inaccessible, etc).
            POST req body should look like: 
        '''
        try:
            result = dict()
            context = controller_strategy.SpecificSubmissionContext(USER_ID, submission_id)
            strategy = controller_strategy.ResubmissionOperationsStrategy()
            resubmission_result = strategy.process_request(context)
        except MultipleInvalid as e:
            path = ''
            for p in e.path:
                if path:
                    path = path+ '->' + p
                else:
                    path = p
            result['errors'] = "Message contents invalid: "+e.msg + " "+ path
            return Response(result, status=400)
        except InvalidId:
            result['errors'] = "Invalid id"
            return Response(result, status=404)
        except DoesNotExist:        # thrown when searching for a submission
            result['errors'] = "Submission not found" 
            return Response(result, status=404)
        except exceptions.ResourceNotFoundError as e:
            result['errors'] = e.strerror
            return Response(result, status=404)
        else:
            if resubmission_result.error_dict:
                result['errors'] = resubmission_result.error_dict 
            if resubmission_result.message:
                result['message'] = resubmission_result.message
            if not resubmission_result.result:      # Nothing has changed - no new job submitted, because the last jobs succeeded
                result['result'] = False
                result['message'] = "Jobs haven't been resubmitted - "+str(result['message']) if 'message' in result else "Jobs haven't been resubmitted. " 
                logging.info("RESULT RESUBMIT JOBS: %s", result)
                return Response(result, status=200) # Should it be 304? (nothing has changed)
            else:
                result['result'] = resubmission_result.result
                logging.info("RESULT RESUBMIT JOBS: %s", result)
                result['message'] = "Jobs resubmitted."+str(result['message']) if 'message' in result else "Jobs resubmitted." 
                return Response(result, status=200)
    

    
# URL: /submissions/123/files/1123445    
class SubmittedFileRequestHandler(APIView):
    ''' Handles the requests for a specific file (existing already).
        GET - retrieves all the information for this file (metadata)
        POST - resubmits the jobs for this file
        PUT - updates a specific part of the metadata.
        DELETE - deletes this file from this submission.'''
    
    def get(self, request, submission_id, file_id, format=None):
        ''' Retrieves the information regarding this file from this submission.
            Returns 404 if the file or the submission don't exist. '''
        try:
            user_id = USER_ID
            result = dict()
#            file_req = controller.get_submitted_file(file_id)
            context = controller_strategy.SpecificFileContext(user_id, submission_id, file_id)
            strategy = controller_strategy.FileRetrievalStrategy()
            file_obj = strategy.process_request(context)
            file_serial = serializers.serialize(file_obj)
        except DoesNotExist:        # thrown when searching for a submission
            result['errors'] = "File not found" 
            return Response(result, status=404)
        except exceptions.ResourceNotFoundError as e:
            result['errors'] = e.strerror
            return Response(result, status=404)
        except InvalidId as e:
            result['errors'] = "Invalid Id"
            return Response(result, status=400)
        else:
            #file_serial = serializers.serialize(file_req)
            result["result"] = file_serial
            res_serial = serializers.serialize_excluding_meta(result)
            logging.debug("RESULT IS: "+res_serial)
            return Response(res_serial, status=200)

            
    def post(self, request, submission_id, file_id, format=None):
        ''' Resubmit jobs for this file - used in case of permission denied.
            The user wants to submit files that mercury does not have permissions on,
            he gets an error message back, and is asked to make a POST req after solving the pb 
            with a parameter indicating how he solved the pb - if he ran himself a worker or just changed file permissions. 
            POST req body should look like: 
            {"permissions_changed : True"} - if he manually changed permissions for this file. '''
        try:
            #data = request.DATA
            #data = utils.unicode2string(data)
            result = dict()
            #validator.submitted_file_schema(data)
            #resubmission_result = controller.resubmit_jobs_for_file(submission_id, file_id)
            
            context = controller_strategy.SpecificFileContext(USER_ID, submission_id, file_id, request.DATA)
            strategy = controller_strategy.ResubmissionOperationsStrategy()
            resubmission_result = strategy.process_request(context)

        except MultipleInvalid as e:
            path = ''
            for p in e.path:
                if path:
                    path = path+ '->' + p
                else:
                    path = p
            result['errors'] = "Message contents invalid: "+e.msg + " "+ path
            return Response(result, status=400)
        except InvalidId:
            result['errors'] = "Invalid id"
            return Response(result, status=404)
        except DoesNotExist:        # thrown when searching for a submission
            result['errors'] = "Submission not found" 
            return Response(result, status=404)
        except exceptions.ResourceNotFoundError as e:
            result['errors'] = e.strerror
            return Response(result, status=404)
        else:
            if resubmission_result.error_dict:
                result['errors'] = resubmission_result.error_dict 
            if resubmission_result.message:
                result['message'] = resubmission_result.message
            if not resubmission_result.result:      # Nothing has changed - no new job submitted, because the last jobs succeeded
                result['result'] = False
                result['message'] = "Jobs haven't been resubmitted - "+str(result['message']) if 'message' in result else "Jobs haven't been resubmitted. " 
                logging.info("RESULT RESUBMIT JOBS: %s", result)
                return Response(result, status=200) # Should it be 304? (nothing has changed)
            else:
                result['result'] = True
                logging.info("RESULT RESUBMIT JOBS: %s", result)
                result['message'] = "Jobs resubmitted."+str(result['message']) if 'message' in result else "Jobs resubmitted." 
                return Response(result, status=200)
                
    
    def put(self, request, submission_id, file_id, format=None):
        ''' Updates the corresponding info for this file.'''
        req_data = request.DATA
        #logging.info("FROM submitted-file's PUT request :-------------"+str(data))
        try:
            user_id = USER_ID
            result = {}
            logging.debug("Received PUT request -- submission id: %s",str(submission_id))
            context = controller_strategy.SpecificFileContext(user_id, submission_id, file_id, req_data)
            strategy = controller_strategy.FileModificationStrategy()
            strategy.process_request(context)
            
            # Working originally:
#            data = utils.unicode2string(data)
#            validator.submitted_file_schema(data)
#            controller.update_file_submitted(submission_id, file_id, data)
            
            
#             user_id = 'ic4'
#            result = dict()
#            logging.debug("Received GET request - submission id:"+submission_id)
#            #submission = controller.get_submission(submission_id)
#            context = controller_strategy.SpecificSubmissionContext(user_id, submission_id)
#            strategy = controller_strategy.SubmissionRetrievalStrategy()
#            submission = strategy.process_request(context)
#            submission_serial = serializers.serialize(submission)
        except MultipleInvalid as e:
            path = ''
            for p in e.path:
                if path:
                    path = path+ '->' + p
                else:
                    path = p
            result['errors'] = "Message contents invalid: "+e.msg + " "+ path
            return Response(result, status=400)
        except InvalidId:
            result['errors'] = "Invalid id"
            return Response(result, status=404)
        except DoesNotExist:        # thrown when searching for a submission
            result['errors'] = "File not found" 
            return Response(result, status=404)
        except exceptions.ResourceNotFoundError as e:
            result['errors'] = e.strerror
            return Response(result, status=404)
        except exceptions.NoEntityIdentifyingFieldsProvided as e:
            result['errors'] = e.strerror
            return Response(result, status=422)     # 422 Unprocessable Entity --The request was well-formed 
                                                    # but was unable to be followed due to semantic errors.
        except exceptions.DeprecatedDocument as e:
            result['errors'] = e.strerror
            return Response(result, status=428)     # Precondition failed prevent- the 'lost update' problem, 
                                                    # where a client GETs a resource's state, modifies it, and PUTs it back 
                                                    # to the server, when meanwhile a third party has modified the state on the server, 
                                                    # leading to a conflict
        else:
            result['message'] = "Successfully updated"
            #result_serial = serializers.serialize(result)
            # return Response(result_serial, status=200)
            return Response(result, status=200)
    
    
    def delete(self, request, submission_id, file_id, format=None):
        ''' Deletes a file. Returns 404 if the file or submission don't exist. '''
        try:
            user_id = USER_ID
            result = dict()
            context = controller_strategy.SpecificFileContext(user_id, submission_id, file_id)
            strategy = controller_strategy.FileDeletionStrategy()
            was_deleted = strategy.process_request(context)
            
            #was_deleted = controller.delete_submitted_file(submission_id, file_id)
        except InvalidId:
            result['errors'] = "Invalid id"
            return Response(result, status=404)
        except DoesNotExist:        # thrown when searching for a submission
            result['errors'] = "File not found" 
            return Response(result, status=404)
        except exceptions.ResourceNotFoundError as e:
            result['errors'] = e.strerror
            return Response(result, status=404)
        except exceptions.OperationNotAllowed as e:
            result['errors'] = e.strerror
            return Response(result, status=424)
        else:
            if was_deleted == True:
                result['result'] = "Successfully deleted"
                return Response(result, status=200)
            else:
                result['result'] = "File was not deleted, probably because it was already submitted to IRODS or in process."
                return Response(result, status=424)
        

#        try:
#            result = dict()
#            subm_statuses = controller.get_submission_status(submission_id)
#        except InvalidId:
#            result['errors'] = "InvalidId"
#            return Response(result, status=404)
#        except DoesNotExist:
#            result['errors'] = "Submission not found"
#            return Response(result, status=404)
#        else:
#            result['result'] = subm_statuses
#            return Response(result, status=200)
#        


###---------------- WORKERS -------------------------------

 
# URL: /submissions/123/files/1123445/worker    
class WorkerSubmittedFileRequestHandler(APIView):
    ''' Handles the requests for a specific file (existing already) that come from the workers.
        PUT - updates a specific part of the metadata.'''
    
    def put(self, request, submission_id, file_id, format=None):
        ''' Updates the corresponding info for this file.'''
        req_data = request.DATA
        #logging.info("FROM submitted-file's PUT request :-------------"+str(data))
        try:
            result = {}
#            print "What type is the data coming in????", type(data)
#            data = utils.unicode2string(data)
#            #print "After converting to string: -------", str(data)
#            validator.submitted_file_schema(data)
#            controller.update_file_submitted(submission_id, file_id, data)

            logging.debug("Received PUT request -- submission id: %s",str(submission_id))
            context = controller_strategy.WorkerSpecificFileContext(submission_id, file_id, request_data=req_data)
            strategy = controller_strategy.FileModificationStrategy()
            print "VARS de Strategy: ", vars(strategy)
            print "CONTEXT type: ", type(context)
            strategy.process_request(context)
            
        except MultipleInvalid as e:
            path = ''
            for p in e.path:
                if path:
                    path = path+ '->' + p
                else:
                    path = p
            result['errors'] = "Message contents invalid: "+e.msg + " "+ path
            return Response(result, status=400)
        except InvalidId:
            result['errors'] = "Invalid id"
            return Response(result, status=404)
        except DoesNotExist:        # thrown when searching for a submission
            result['errors'] = "File not found" 
            return Response(result, status=404)
        except exceptions.ResourceNotFoundError as e:
            result['errors'] = e.strerror
            return Response(result, status=404)
        except exceptions.NoEntityIdentifyingFieldsProvided as e:
            result['errors'] = e.strerror
            return Response(result, status=422)     # 422 Unprocessable Entity --The request was well-formed 
                                                    # but was unable to be followed due to semantic errors.
        except exceptions.DeprecatedDocument as e:
            result['errors'] = e.strerror
            return Response(result, status=428)     # Precondition failed prevent- the 'lost update' problem, 
                                                    # where a client GETs a resource's state, modifies it, and PUTs it back 
                                                    # to the server, when meanwhile a third party has modified the state on the server, 
                                                    # leading to a conflict
        else:
            result['message'] = "Successfully updated"
            #result_serial = serializers.serialize(result)
            # return Response(result_serial, status=200)
            return Response(result, status=200)
    


# ------------------- ENTITIES -----------------------------

# -------------------- LIBRARIES ---------------------------

class LibrariesMainPageRequestHandler(APIView):
    ''' Handles requests /submissions/123/files/3/libraries/.
        GET - retrieves all the libraries that this file contains as metadata.
        POST - adds a new library to the metadata of this file'''
    def get(self,  request, submission_id, file_id, format=None):
        try:
            result = dict()
            libs = controller.get_all_libraries(submission_id, file_id)
        except InvalidId:
            result['errors'] = "Invalid id"
            return Response(result, status=404)
        except DoesNotExist:        # thrown when searching for a submission
            result['errors'] = "Submission not found" 
            return Response(result, status=404)
        except exceptions.ResourceNotFoundError as e:
            result['errors'] = e.strerror
            return Response(result, status=404)
        else:
            result['result'] = libs
            result_serial = serializers.serialize_excluding_meta(result)
            logging.debug("RESULT IS: "+result_serial)
            return Response(result_serial, status=200)
        
    
    def post(self,  request, submission_id, file_id, format=None):
        ''' Handles POST request - adds a new library to the metadata
            for this file. Returns True if the library has been 
            successfully added, False if not.
        '''
        try:
#           data = request.POST['_content']
            result = dict()
            data = request.DATA
            data = utils.unicode2string(data)
            validator.library_schema(data)
            controller.add_library_to_file_mdata(submission_id, file_id, data)
        except MultipleInvalid as e:
            path = ''
            for p in e.path:
                if path:
                    path = path+ '->' + p
                else:
                    path = p
            result['error'] = "Message contents invalid: "+e.msg + " "+ path
            return Response(result, status=400)
        except InvalidId:
            result['errors'] = "Invalid id"
            return Response(result, status=404)
        except DoesNotExist:        # thrown when searching for a submission
            result['errors'] = "Submission not found" 
            return Response(result, status=404)
        except exceptions.ResourceNotFoundError as e:
            result['errors'] = e.strerror
            return Response(result, status=404)
        except exceptions.NoEntityIdentifyingFieldsProvided as e:
            result['errors'] = e.strerror
            return Response(result, status=422)
        except exceptions.NoEntityCreated as e:
            result['errors'] = e.strerror
            return Response(result, status=422)     # 422 = Unprocessable entity => either empty json or invalid fields
        except exceptions.EditConflictError as e:
            result['errors'] = e.strerror
            return Response(result, status=409)     # 409 = EditConflict
        else:
            result['result'] = "Library added"
            #result = serializers.serialize(result)
            logging.debug("RESULT IS: "+str(result))
            return Response(result, status=200)
            
    

class LibraryRequestHandler(APIView):
    ''' Handles the requests for a specific library (existing already).
        GET - retrieves the library identified by the id.
        PUT - updates fields of the metadata for the specified library
        DELETE - deletes the specified library from the library list of this file.
    '''
    def get(self, request, submission_id, file_id, library_id, format=None):
        try:
            result = dict()
            lib = controller.get_library(submission_id, file_id, library_id)
        except InvalidId:
            result['error'] = "Invalid id"
            return Response(result, status=404)
        except DoesNotExist:        # thrown when searching for a submission
            result['errors'] = "Submission not found" 
            return Response(result, status=404)
        except exceptions.ResourceNotFoundError as e:
            result['errors'] = e.strerror
            return Response(result, status=404)
#        except exceptions.EntityNotFound as e:
#            result['errors'] = e.message
#            return Response(result, status=404)
        else:
            result['result'] = lib
            result_serial = serializers.serialize_excluding_meta(result)
            logging.debug("RESULT IS: "+result_serial)
            return Response(result_serial, status=200)
        

    def put(self, request, submission_id, file_id, library_id, format=None):
        ''' Updates the metadata associated to a particular library.'''
        try:
#            result = dict()
#            new_data = dict()
#            for elem in data:
#                key = ''.join(chr(ord(c)) for c in elem)
#                val = ''.join(chr(ord(c)) for c in data[elem])
#                new_data[key] = val
            data = request.DATA
            data = utils.unicode2string(data)
            validator.library_schema(data)
            result = dict()
            was_updated = controller.update_library(submission_id, file_id, library_id, data)
        except MultipleInvalid as e:
            path = ''
            for p in e.path:
                if path:
                    path = path+ '->' + p
                else:
                    path = p
            result['error'] = "Message contents invalid: "+e.msg + " "+ path
            return Response(result, status=400)
        except InvalidId:
            result['errors'] = "Invalid id"
            return Response(result, status=404)
        except DoesNotExist:        # thrown when searching for a submission
            result['errors'] = "Submission not found" 
            return Response(result, status=404)
        except KeyError:
            result['errors'] = "Key not found. Please include only data according to the model."
            return Response(result, status=400)
        except exceptions.NoEntityIdentifyingFieldsProvided as e:
            result['errors'] = e.strerror
            return Response(result, status=422)     # 422 Unprocessable Entity --The request was well-formed but was unable to be followed due to semantic errors.
        except exceptions.ResourceNotFoundError as e:
            result['erors'] = e.strerror
            return Response(result, status=404)
        except exceptions.DeprecatedDocument as e:
            result['errors'] = e.strerror
            return Response(result, status=428)     # Precondition failed prevent- the 'lost update' problem, 
                                                    # where a client GETs a resource's state, modifies it, and PUTs it back 
                                                    # to the server, when meanwhile a third party has modified the state 
                                                    # on the server, leading to a conflict
        else:
            if was_updated:
                result['message'] = "Successfully updated"
                return Response(result, status=200)
            else:
                result['message'] = "Not modified"
                return Response(result, status=304)
            #result_serial = serializers.serialize(result)
            # return Response(result_serial, status=200)
            return Response(result, status=200)
    
    
    def delete(self, request, submission_id, file_id, library_id, format=None):
        try:
            result = dict()
            was_deleted = controller.delete_library(submission_id, file_id, library_id)
        except InvalidId:
            result['errors'] = "Invalid id"
            return Response(result, status=404)
        except DoesNotExist:        # thrown when searching for a submission
            result['errors'] = "File not found" 
            return Response(result, status=404)
        except exceptions.ResourceNotFoundError as e:
            result['errors'] = e.strerror
            return Response(result, status=404)
        else:
            if was_deleted:
                result['result'] = "Successfully deleted"
                result_serial = serializers.serialize(result)
                logging.debug("RESULT IS: "+result_serial)
                return Response(result_serial, status=200)
            else:
                result['result'] = "Library couldn't be deleted"
                result_serial = serializers.serialize(result)
                logging.debug("RESULT IS: "+result_serial)
                return Response(result_serial, status=304)
            
    
    
    
class SamplesMainPageRequestHandler(APIView):
    ''' Handles requests for /submissions/123/files/12/samples/
        GET - retrieves the list of all samples
        POST - adds a new sample to the list of samples that the file has.
    '''
    
    def get(self,  request, submission_id, file_id, format=None):
        ''' Handles requests /submissions/123/files/3/samples/.
            GET - retrieves all the samples that this file contains as metadata.
            POST - adds a new sample to the metadata of this file.
        '''
        try:
            result = dict()
            samples = controller.get_all_samples(submission_id, file_id)
        except InvalidId:
            result['errors'] = "Invalid id"
            return Response(result, status=404)
        except DoesNotExist:        # thrown when searching for a submission
            result['errors'] = "Submission not found" 
            return Response(result, status=404)
        except exceptions.ResourceNotFoundError as e:
            result['errors'] = e.strerror
            return Response(result, status=404)
        else:
            result['result'] = samples
            logging.debug("NOT SERIALIZED RESULT: "+str([(s.name,s.internal_id) for s in samples]))
            result_serial = serializers.serialize_excluding_meta(result)
            print "PRINT RESULT SERIAL: ", result_serial
            logging.debug("RESULT IS: "+result_serial)
            return Response(result_serial, status=200)
        
    
    def post(self,  request, submission_id, file_id, format=None):
        ''' Handles POST request - adds a new sample to the metadata
            for this file. Returns True if the sample has been 
            successfully added, False if not.
        '''
        try:
            result = dict()
            data = request.DATA
            data = utils.unicode2string(data)
            validator.sample_schema(data)
            controller.add_sample_to_file_mdata(submission_id, file_id, data)
        except MultipleInvalid as e:
            path = ''
            for p in e.path:
                if path:
                    path = path+ '->' + p
                else:
                    path = p
            result['error'] = "Message contents invalid: "+e.msg + " "+ path
            return Response(result, status=400)
        except InvalidId:
            result['errors'] = "Invalid id"
            return Response(result, status=404)
        except DoesNotExist:        # thrown when searching for a submission
            result['errors'] = "Submission not found" 
            return Response(result, status=404)
        except exceptions.ResourceNotFoundError as e:
            result['errors'] = e.strerror
            return Response(result, status=404)
        except exceptions.NoEntityIdentifyingFieldsProvided as e:
            result['errors'] = e.strerror
            return Response(result, status=422)
        except exceptions.NoEntityCreated as e:
            result['errors'] = e.strerror
            return Response(result, status=422)     # 422 = Unprocessable entity => either empty json or invalid fields
        except exceptions.EditConflictError as e:
            result['errors'] = e.strerror
            return Response(result, status=409)     # 409 = EditConflict

        else:
            result['result'] = "Sample added"
            #result = serializers.serialize(result)
            logging.debug("RESULT IS: "+str(result))
            return Response(result, status=200)
        
    
    
class SampleRequestHandler(APIView):
    ''' Handles requests for a specific sample (existing already).
        GET - retrieves the sample identified by the id.
        PUT - updates fields of the metadata for the specified sample
        DELETE - deletes the specified sample from the sample list of this file.
    '''
    
    def get(self, request, submission_id, file_id, sample_id, format=None):
        ''' Retrieves a specific sampl, identified by sample_id.'''
        try:
            result = dict()
            print "VIEW -------- SAMPLE ID IS: ", sample_id
            sample = controller.get_sample(submission_id, file_id, sample_id)
            
        except InvalidId:
            result['errors'] = "Invalid id"
            return Response(result, status=404)
        except DoesNotExist:        # thrown when searching for a submission
            result['errors'] = "Submission not found" 
            return Response(result, status=404)
        except exceptions.ResourceNotFoundError as e:
            result['errors'] = e.strerror
            return Response(result, status=404)
#        except exceptions.EntityNotFound as e:
#            result['errors'] = e.message
#            return Response(result, status=404)
        else:
            result['result'] = sample
            result_serial = serializers.serialize_excluding_meta(result)
            logging.debug("RESULT IS: "+result_serial)
            return Response(result_serial, status=200)
        

    def put(self, request, submission_id, file_id, sample_id, format=None):
        ''' Updates the metadata associated to a particular sample.'''
        #logging.info("FROM PUT request - req looks like:-------------"+str(request))
        try:
            data = request.DATA
            data = utils.unicode2string(data)
            validator.sample_schema(data)
            result = dict()
            was_updated = controller.update_sample(submission_id, file_id, sample_id, data)
        except MultipleInvalid as e:
            path = ''
            for p in e.path:
                if path:
                    path = path+ '->' + p
                else:
                    path = p
            result['error'] = "Message contents invalid: "+e.msg + " "+ path
            return Response(result, status=400)
        except InvalidId:
            result['errors'] = "Invalid id"
            return Response(result, status=404)
        except DoesNotExist:        # thrown when searching for a submission
            result['errors'] = "Submission not found" 
            return Response(result, status=404)
        except KeyError:
            result['errors'] = "Key not found. Please include only data according to the model."
            return Response(result, status=400)
        except exceptions.NoEntityIdentifyingFieldsProvided as e:
            result['errors'] = e.strerror
            return Response(result, status=422)     # 422 Unprocessable Entity --The request was well-formed 
                                                    # but was unable to be followed due to semantic errors.
        except exceptions.ResourceNotFoundError as e:
            result['errors'] = e.strerror
            return Response(result, status=404)
        except exceptions.DeprecatedDocument as e:
            result['errors'] = e.strerror
            return Response(result, status=428)     # Precondition failed prevent- the 'lost update' problem, 
                                                    # where a client GETs a resource's state, modifies it, and PUTs it back 
                                                    # to the server, when meanwhile a third party has modified the state on the server, leading to a conflict
        else:
            print "WAS UPDATED? -- from views: ", was_updated
            if was_updated == 1:
                result['message'] = "Successfully updated"
                return Response(result, status=200)
            else:
                result['message'] = "Not modified"
                return Response(result, status=304)
            #result_serial = serializers.serialize(result)
            # return Response(result_serial, status=200)
            return Response(result, status=200)
    
    
    def delete(self, request, submission_id, file_id, sample_id, format=None):
        try:
            result = dict()
            was_deleted = controller.delete_sample(submission_id, file_id, sample_id)
        except InvalidId:
            result['errors'] = "Invalid id"
            return Response(result, status=404)
        except DoesNotExist:        # thrown when searching for a submission
            result['errors'] = "File not found" 
            return Response(result, status=404)
        except exceptions.ResourceNotFoundError as e:
            result['errors'] = e.strerror
            return Response(result, status=404)
        else:
            if was_deleted:
                result['result'] = "Successfully deleted"
                result_serial = serializers.serialize(result)
                logging.debug("RESULT IS: "+result_serial)
                return Response(result_serial, status=200)
            else:
                result['result'] = "Sample couldn't be deleted"
                result_serial = serializers.serialize(result)
                logging.debug("RESULT IS: "+result_serial)
                return Response(result_serial, status=304)
            


    
class StudyMainPageRequestHandler(APIView):
    ''' Handles requests for /submissions/123/files/12/studies/
        GET - retrieves the list of all studies
        POST - adds a new study to the list of studies that the file has.
    '''
    
    def get(self,  request, submission_id, file_id, format=None):
        try:
            result = dict()
            studies = controller.get_all_studies(submission_id, file_id)
        except InvalidId:
            result['errors'] = "Invalid id"
            return Response(result, status=404)
        except DoesNotExist:        # thrown when searching for a submission
            result['errors'] = "Submission not found" 
            return Response(result, status=404)
        except exceptions.ResourceNotFoundError as e:
            result['errors'] = e.strerror
            return Response(result, status=404)
        else:
            result['result'] = studies
            result_serial = serializers.serialize_excluding_meta(result)
            logging.debug("RESULT IS: "+result_serial)
            return Response(result_serial, status=200)
        
    
    def post(self,  request, submission_id, file_id, format=None):
        ''' Handles POST request - adds a new study to the metadata
            for this file. Returns True if the study has been 
            successfully added, False if not.
        '''
        try:
#            data = request.POST['_content']
            result = dict()
            req_data = request.DATA if hasattr(request, 'DATA') else None
            req_data = utils.unicode2string(req_data)
            validator.study_schema(req_data)
            controller.add_study_to_file_mdata(submission_id, file_id, req_data)
        except MultipleInvalid as e:
            path = ''
            for p in e.path:
                if path:
                    path = path+ '->' + p
                else:
                    path = p
            result['error'] = "Message contents invalid: "+e.msg + " "+ path
            return Response(result, status=400)
        except InvalidId:
            result['errors'] = "Invalid id"
            return Response(result, status=404)
        except DoesNotExist:        # thrown when searching for a submission
            result['errors'] = "Submission not found" 
            return Response(result, status=404)
        except exceptions.ResourceNotFoundError as e:
            result['errors'] = e.strerror
            return Response(result, status=404)
        except exceptions.NoEntityIdentifyingFieldsProvided as e:
            result['errors'] = e.strerror
            return Response(result, status=422)
        except exceptions.NoEntityCreated as e:
            result['errors'] = e.strerror
            return Response(result, status=422)     # 422 = Unprocessable entity => either empty json or invalid fields
        except exceptions.EditConflictError as e:
            result['errors'] = e.strerror
            return Response(result, status=409)     # 409 = EditConflict

        else:
            result['result'] = "Study added"
            #result = serializers.serialize(result)
            logging.debug("RESULT IS: "+str(result))
            return Response(result, status=200)
        
            
    
class StudyRequestHandler(APIView):
    ''' Handles requests for a specific study (existing already).
        GET - retrieves the study identified by the id.
        PUT - updates fields of the metadata for the specified study
        DELETE - deletes the specified study from the study list of this file.
    '''


    def get(self, request, submission_id, file_id, study_id, format=None):
        try:
            print "STUDY IDDDDDDDDDDD", study_id
            result = dict()
            lib = controller.get_study(submission_id, file_id, study_id)
        except InvalidId:
            result['errors'] = "Invalid id"
            return Response(result, status=404)
        except DoesNotExist:        # thrown when searching for a submission
            result['errors'] = "Submission not found" 
            return Response(result, status=404)
        except exceptions.ResourceNotFoundError as e:
            result['errors'] = e.strerror
            return Response(result, status=404)
#        except exceptions.EntityNotFound as e:
#            result['errors'] = e.message
#            return Response(result, status=404)
        else:
            result['result'] = lib
            result_serial = serializers.serialize_excluding_meta(result)
            logging.debug("RESULT IS: "+result_serial)
            return Response(result_serial, status=200)
        

    def put(self, request, submission_id, file_id, study_id, format=None):
        ''' Updates the metadata associated to a particular study.'''
        logging.info("FROM PUT request - req looks like:-------------"+str(request))
        req_data = request.DATA if hasattr(request, 'DATA') else None
        try:
            result = dict()
            req_data = utils.unicode2string(req_data)
            was_updated = controller.update_study(submission_id, file_id, study_id, req_data)
        except InvalidId:
            result['errors'] = "Invalid id"
            return Response(result, status=404)
        except DoesNotExist:        # thrown when searching for a submission
            result['errors'] = "Submission not found" 
            return Response(result, status=404)
        except KeyError:
            result['errors'] = "Key not found. Please include only data according to the model."
            return Response(result, status=400)
        except exceptions.NoEntityIdentifyingFieldsProvided as e:
            result['errors'] = e.strerror
            return Response(result, status=422)     # 422 Unprocessable Entity --The request was well-formed 
                                                    # but was unable to be followed due to semantic errors.
        except exceptions.ResourceNotFoundError as e:
            result['erors'] = e.strerror
            return Response(result, status=404)
        except exceptions.DeprecatedDocument as e:
            result['errors'] = e.strerror
            return Response(result, status=428)     # Precondition failed prevent- the 'lost update' problem, 
                                                    # where a client GETs a resource's state, modifies it, and PUTs it back 
                                                    # to the server, when meanwhile a third party has modified the state on the server, 
                                                    # leading to a conflict
#        except exceptions.ResourceNotFoundError as e:
#            result['errors'] = e.message
#            return Response(result, status=404)
        else:
            if was_updated == 1:
                result['message'] = "Successfully updated"
                return Response(result, status=200)
            else:
                result['message'] = "Not modified"
                return Response(result, status=304)
            #result_serial = serializers.serialize(result)
            # return Response(result_serial, status=200)
            return Response(result, status=200)
    
    
    def delete(self, request, submission_id, file_id, study_id, format=None):
        try:
            result = dict()
            was_deleted = controller.delete_study(submission_id, file_id, study_id)
        except InvalidId:
            result['errors'] = "Invalid id"
            return Response(result, status=404)
        except DoesNotExist:        # thrown when searching for a submission
            result['errors'] = "File not found" 
            return Response(result, status=404)
        except exceptions.ResourceNotFoundError as e:
            result['errors'] = e.strerror
            return Response(result, status=404)
        else:
            if was_deleted:
                result['result'] = "Successfully deleted"
                result_serial = serializers.serialize(result)
                logging.debug("RESULT IS: "+result_serial)
                return Response(result_serial, status=200)
            else:
                result['result'] = "Study couldn't be deleted"
                result_serial = serializers.serialize(result)
                logging.debug("RESULT IS: "+result_serial)
                return Response(result_serial, status=304)
                
    
    
# ------------------------------- IRODS -----------------------------


# submissions/<submission_id>/irods/
# Submit Submission to iRODS:
class SubmissionIRODSRequestHandler(APIView):
    def post(self, request, submission_id, format=None):
        ''' Makes the submission to IRODS of all the files 
            contained in this submission in 2 steps hidden
            from the user: first the metadata is attached to
            the files while they are still in the staging area,
            then the files are all moved to the permanent collection.'''
        try:
#            data = None
#            if hasattr(request, 'DATA'):
#                data = request.DATA
#                data = utils.unicode2string(data)
            result = dict()
            #irods_submission_result = controller.submit_all_to_irods(submission_id, data)
            req_data = request.DATA if hasattr(request, 'DATA') else None
            context = controller_strategy.SpecificSubmissionContext(USER_ID, submission_id, req_data)
            strategy = controller_strategy.BackendSubmissionStrategy()
            submission_result = strategy.process_request(context)
        except InvalidId:
            result['errors'] = "InvalidId"
            result['result'] = False
            return Response(result, status=400)
        except DoesNotExist:
            result['errors'] = "Submitted file not found"
            result['result'] = False
            return Response(result, status=404)
        except exceptions.OperationNotAllowed as e:
            result['errors'] = e.strerror
            result['result'] = False
            return Response(result, status=424)
        except exceptions.OperationAlreadyPerformed as e:
            result['errors'] = e.strerror
            result['result'] = False
            return Response(result, status=304)
        else:
            result['result'] = submission_result.result
            return Response(result, status=202)


# submissions/<submission_id>/files/<file_id>/irods/
# Submit ONE File to iRODS:
class SubmittedFileIRODSRequestHandler(APIView):
    def post(self, request, submission_id, file_id, format=None):
        ''' Submits the file to iRODS in 2 steps (hidden from the user):
            first the metadata is attached to the file while it is still
            in the staging area, then it is moved to the permanent iRODS coll.'''
        try:
            req_data = request.DATA if hasattr(request, 'DATA') else None
            result = dict()
            context = controller_strategy.SpecificFileContext(USER_ID, submission_id, file_id, req_data)
            strategy = controller_strategy.BackendSubmissionStrategy()
            submission_result = strategy.process_request(context)
        except InvalidId:
            result['errors'] = "InvalidId"
            return Response(result, status=404)
        except DoesNotExist:
            result['errors'] = "Submitted file not found"
            return Response(result, status=404)
        except exceptions.OperationNotAllowed as e:
            result['errors'] = e.strerror
            return Response(result, status=424)
        except exceptions.IncorrectMetadataError as e:
            result['errors'] = e.strerror
            return Response(result, status=424)
        else:
            result['result'] = submission_result.result
            if hasattr(submission_result, 'error_dict'):
                result['errors'] = submission_result.error_dict
                return Response(result, status=424)
            return Response(result, status=200)
            
       
# submissions/<submission_id>/irods/meta/'
# Manipulating metadata in iRODS:
class SubmissionIRODSMetaRequestHandler(APIView):
    def post(self, request, submission_id, format=None):
        ''' Attaches the metadata to all the files in the submission, 
            while they are still in the staging area'''
        try:
#            data = None
#            if hasattr(request, 'DATA'):
#                data = request.DATA
#                data = utils.unicode2string(data)
            result = dict()
            req_data = request.DATA if hasattr(request, 'DATA') else None
            context = controller_strategy.SpecificSubmissionContext(USER_ID, submission_id, req_data)
            strategy = controller_strategy.AddMetadataToBackendFileStrategy()
            submission_result = strategy.process_request(context)
            
            #added_meta = controller.add_meta_to_all_staged_files(submission_id, data)
        except InvalidId:
            result['errors'] = "InvalidId"
            return Response(result, status=404)
        except DoesNotExist:
            result['errors'] = "Submitted file not found"
            return Response(result, status=404)
        except exceptions.OperationNotAllowed as e:
            result['errors'] = e.strerror
            return Response(result, status=424)
        except exceptions.IncorrectMetadataError as e:
            result['errors'] = e.strerror
            return Response(result, status=424)
        else:
            result['result'] = submission_result.result
            if submission_result.result == False:
                if submission_result.error_dict:
                    result['errors'] = submission_result.error_dict
                return Response(result, status=424)
            return Response(result, status=202) 

    
    def delete(self, request, submission_id, format=None):
        ''' Deletes all the metadata from the files together 
            with the associated tasks from the task dict'''
        pass
    
    
# submissions/<submission_id>/files/<file_id>/irods/meta/
class SubmittedFileIRODSMetaRequestHandler(APIView):
    def post(self, request, submission_id, file_id, format=None):
        ''' Attaches the metadata to the file, while it's still in the staging area'''
        try:
            result = dict()
            #added_meta = controller.add_meta_to_staged_file(file_id)
            req_data = request.DATA if hasattr(request, 'DATA') else None
            context = controller_strategy.SpecificFileContext(USER_ID, submission_id, file_id, req_data)
            strategy = controller_strategy.AddMetadataToBackendFileStrategy()
            submission_result = strategy.process_request(context)
        except InvalidId:
            result['errors'] = "InvalidId"
            return Response(result, status=404)
        except DoesNotExist:
            result['errors'] = "Submitted file not found"
            return Response(result, status=404)
        except exceptions.OperationNotAllowed as e:
            result['errors'] = e.message
            return Response(result, status=424)
        except exceptions.IncorrectMetadataError as e:
            result['errors'] = e.message
            return Response(result, status=424)
        else:
            result['result'] = submission_result.result
            if submission_result.result:
                return Response(result, status=202)
            if submission_result.error_dict:
                result['errors'] = submission_result.error_dict
            return Response(result, status=424) 

       

# submissions/<submission_id>/irods/irods-files/
class SubmissionToiRODSPermanentRequestHandler(APIView):
       
    def post(self, request, submission_id, format=None):
        ''' Moves all the files in a submission from the staging area to the
            iRODS permanent and non-modifyable collection. '''
        try:
#            data = None
#            if hasattr(request, 'DATA'):
#                data = request.DATA
#                data = utils.unicode2string(data)
            result = dict()
            #moved_files = controller.move_all_to_iRODS_permanent_coll(submission_id, data)
            req_data = request.DATA if hasattr(request, 'DATA') else None
            context = controller_strategy.SpecificSubmissionContext(USER_ID, submission_id, req_data)
            strategy = controller_strategy.MoveFilesToPermanentBackendCollection()
            submission_result = strategy.process_request(context)
        except InvalidId:
            result['errors'] = "InvalidId"
            return Response(result, status=404)
        except DoesNotExist:
            result['errors'] = "Submitted file not found"
            return Response(result, status=404)
        except exceptions.OperationNotAllowed as e:
            result['errors'] = e.message
            return Response(result, status=424)
        except exceptions.IncorrectMetadataError as e:
            result['errors'] = e.message
            return Response(result, status=424)
        else:
            result['result'] = submission_result.result
            if submission_result.result:
                return Response(result, status=202)
            if submission_result.error_dict:
                result['errors'] = submission_result.error_dict
            return Response(result, status=424) 

       
       
# submissions/<submission_id>/files/<file_id>/irods/irods-files
class SubmittedFileToiRODSPermanentRequestHandler(APIView):
    
    def post(self, request, submission_id, file_id, format=None):
        ''' Moves a staged file from the staging area to the
            iRODS permanent and non-modifyable collection. '''
        try:
            result = dict()
            #moved_file = controller.move_file_to_iRODS_permanent_coll(file_id)
            #req_data = request.DATA if hasattr(request, 'DATA') else None
            context = controller_strategy.SpecificFileContext(USER_ID, submission_id)
            strategy = controller_strategy.MoveFilesToPermanentBackendCollection()
            submission_result = strategy.process_request(context)
        except InvalidId:
            result['errors'] = "InvalidId"
            return Response(result, status=404)
        except DoesNotExist:
            result['errors'] = "Submitted file not found"
            return Response(result, status=404)
        except exceptions.OperationNotAllowed as e:
            result['errors'] = e.message
            return Response(result, status=424)
        except exceptions.IncorrectMetadataError as e:
            result['errors'] = e.message
            return Response(result, status=424)
        else:
            result['result'] = submission_result.result
            if submission_result.result == True:
                return Response(result, status=202)
            else:
                if submission_result.message:
                    result['errors'] = submission_result.message
                return Response(result, status=424) 
       
       
# ------------------------------ NOT USED ---------------------------



class GetFolderContent(APIView):
    def post(self, request, format=None):
        data = request.DATA
        print "Data received - POST request: ", data
        # CALL getFolder on WORKER...
        return Response({"rasp" : "POST"})
    
         
# Get all submissions of this user_id
class GetAllUserSubmissions(APIView):
    def get(self, request, user_id, format=None):
        submission_list = models.Submission.objects.filter(sanger_user_id=user_id)
        return Response(submission_list)


         
        