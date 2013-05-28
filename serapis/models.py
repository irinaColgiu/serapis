
from serapis import exceptions
from mongoengine import *
from serapis.constants import *
from bson.objectid import ObjectId
#from mongoengine.base import ObjectIdField

import re
import simplejson
import logging



FILE_TYPES = (BAM_FILE, VCF_FILE)
SUBMISSION_STATUS = ("SUCCESS", "FAILURE", "PENDING", "IN_PROGRESS", "PARTIAL_SUCCESS")
# maybe also: PENDING, STARTED, RETRY - if using result-backend

#FILE_HEADER_MDATA_STATUS = ("PRESENT", "MISSING")
#FILE_SUBMISSION_STATUS = ("SUCCESS", "FAILURE", "PENDING", "IN_PROGRESS", "READY_FOR_SUBMISSION")
#FILE_UPLOAD_JOB_STATUS = ("SUCCESS", "FAILURE", "IN_PROGRESS", "PERMISSION_DENIED")
#FILE_MDATA_STATUS = ("COMPLETE", "INCOMPLETE", "IN_PROGRESS", "IS_MINIMAL")

#("SUCCESSFULLY_UPLOADED", "WAITING_ON_METADATA", "FAILURE", "PENDING", "IN_PROGRESS")

#FILE_SUBMISSION_STATUS = ("COMPLETED", "NOT_COMPLETED")
#FILE_UPLOAD_TASK_STATUS = ("FINISHED", "NOT_FINISHED")
#FILE_MDATA_TASK_STATUS = ("FINISHED", "NOT_FINISHED")



# ------------------- Model classes ----------------------------------
    
#ENTITY_APP_MDATA_FIELDS = ['is_complete', 'has_minimal', 'last_updates_source']
ENTITY_APP_MDATA_FIELDS = ['last_updates_source']
ENTITY_IDENTITYING_FIELDS = ['internal_id', 'name', 'accession_number']

FILE_SUBMITTED_META_FIELDS = ['file_upload_job_status', 
                              'file_header_parsing_job_status', 
                              'header_has_mdata', 
                              'file_update_mdata_job_status', 
                              'last_updates_source',
                              'file_mdata_status',
                              'file_submission_status',
                              #'file_error_log',
                              ]
  

class Entity(DynamicEmbeddedDocument):
    internal_id = IntField()
    name = StringField()    # UNIQUE
    
    # APPLICATION METADATA FIELDS:
    is_complete = BooleanField()
    has_minimal = BooleanField(default=False)
    last_updates_source = DictField()        # keeps name of the field - source that last modified this field
    
    meta = {
        'allow_inheritance': True,
    }

    
    def __eq__(self, other):
        if other == None:
            return False
        for id_field in ENTITY_IDENTITYING_FIELDS:
            if id_field in other and hasattr(self, id_field) and other[id_field] != None and getattr(self, id_field) != None:
                return other[id_field] == getattr(self, id_field)
        return False

    

class Study(Entity):
    accession_number = StringField()
    study_type = StringField()
    study_title = StringField()
    faculty_sponsor = StringField()
    ena_project_id = StringField()
    reference_genome = StringField()
    

class Library(Entity):
    library_type = StringField()
    public_name = StringField() 


class Sample(Entity):          # one sample can be member of many studies
    accession_number = StringField()         # each sample relates to EXACTLY 1 individual
    sanger_sample_id = StringField()
    public_name = StringField()
    sample_tissue_type = StringField() 
    reference_genome = StringField()
    
    # Fields relating to the individual:
    taxon_id = StringField()
    gender = StringField()
    cohort = StringField()
    ethnicity = StringField()
    country_of_origin = StringField()
    geographical_region = StringField()
    organism = StringField()
    common_name = StringField()          # This is the field name given for mdata in iRODS /seq
    
  
    
class SubmittedFile(DynamicDocument):
    #submission_id = StringField(required=True)
    #file_id = Field(required=True)
    submission_id = StringField()
    id = ObjectId()
    file_type = StringField(choices=FILE_TYPES)
    file_path_client = StringField()
    file_path_irods = StringField()    
    md5 = StringField()
    
    study_list = ListField(EmbeddedDocumentField(Study))
    library_list = ListField(EmbeddedDocumentField(Library))
    sample_list = ListField(EmbeddedDocumentField(Sample))
    seq_centers = ListField(StringField())          # List of sequencing centers where the data has been sequenced
    
    
    ############### APPLICATION - LEVEL METADATA #######################

    ''' Version field holds a list of 4 version numbers(int) - each nr having a different meaning:
        0 1 2 3:
        - 1st elem of the list = version of the file mdata (fields specific to the file, excluding the lists of entities)
        - 2nd elem of the list = version of the list of samples mdata
        - 3rd elem of the list = version of the list of libraries mdata
        - 4th elem of the list = version of the list of studies mdata
        The version numbers corresponding to 2,3,4th elem of the list are independent of each other,
        while the 1st version nr depends on all the others 
        => any change of version in elements 2,3,4 will result in a change of elem 1 of the list.
    '''
    version = ListField(default=lambda : [0,0,0,0])
    
    ######################## STATUSES ##################################
    # UPLOAD JOB:
    file_upload_job_status = StringField(choices=FILE_UPLOAD_JOB_STATUS)        #("SUCCESS", "FAILURE", "IN_PROGRESS", "PERMISSION_DENIED")
    
    # FIELDS FOR FILE MDATA:
    has_minimal = BooleanField(default=False)
    
    # HEADER PARSING JOB:
    file_header_parsing_job_status = StringField(choices=HEADER_PARSING_JOB_STATUS) # ("SUCCESS", "FAILURE")
    header_has_mdata = BooleanField()
    
    # UPDATE MDATA JOB:
    file_update_mdata_job_status = StringField(choices=UPDATE_MDATA_JOB_STATUS) #UPDATE_MDATA_JOB_STATUS = ("SUCCESS", "FAILURE", "PENDING", "IN_PROGRESS")
    
    #GENERAL STATUSES -- NOT MODIFYABLE BY THE WORKERS, ONLY BY CONTROLLER
    file_mdata_status = StringField(choices=FILE_MDATA_STATUS)              # ("COMPLETE", "INCOMPLETE", "IN_PROGRESS", "IS_MINIMAL"), general status => when COMPLETE file can be submitted to iRODS
    file_submission_status = StringField(choices=FILE_SUBMISSION_STATUS)    # ("SUCCESS", "FAILURE", "PENDING", "IN_PROGRESS", "READY_FOR_SUBMISSION")    
    
    #file_error_log = DictField()                        # dict containing: key = sender, value = List of errors
    file_error_log = ListField(StringField)
    missing_entities_error_dict = DictField()           # dictionary of missing mdata in the form of:{'study' : [ "name" : "Exome...", ]} 
    not_unique_entity_error_dict = DictField()          # List of resources that aren't unique in seqscape: {field_name : [field_val,...]}
    meta = {                                            # Mongoengine specific field for metadata.
            'allow_inheritance': True
            }
    
    last_updates_source = DictField()                # keeps name of the field - source that last modified this field 
    
    
    

class BAMFile(SubmittedFile):
    bam_type = StringField()
    #lane_nrs_list = ListField()
    
    
class VCFFile(SubmittedFile):
    file_format = StringField(choices=VCF_FORMATS)
    used_samtools = BooleanField()
    used_unified_genotyper = BooleanField()
    reference = StringField()
     
        
class Submission(DynamicDocument):
    sanger_user_id = StringField()
    submission_status = StringField(choices=SUBMISSION_STATUS)
    #files_list = ListField(EmbeddedDocumentField(SubmittedFile))
    #files_list = ListField(ReferenceField(SubmittedFile, reverse_delete_rule=CASCADE))
    files_list = ListField()        # list of ObjectIds - representing SubmittedFile ids
    meta = {
        'indexes': ['sanger_user_id', '_id'],
            }
    
 

    # OPERATIONS ON INDIVIDUAL FILES:
#    def get_file_by_id(self, file_id):
#        ''' Returns the corresponding SubmittedFile identified by file_id
#            and None if there is no file with this id. '''
#        for f in self.files_list:
#            if f.file_id == int(file_id):
#                return f
#        return None
#
#    def delete_file_by_id(self, file_id):
#        ''' Deletes the file identified by the file_id and raises a
#            ResoueceDoesNotExist if there is not file with this id. '''
#        file_to_del = self.get_file_by_id(file_id)
#        if file_to_del == None:
#            raise exceptions.ResourceNotFoundError(file_id, "File not found")
#        else:
#            self.files_list.remove(file_to_del)


    
#    meta = {
#        'allow_inheritance': True,
#        'indexes': ['-created_at', 'slug'],
#        'ordering': ['-created_at']
#    }

class MyEmbed(EmbeddedDocument):
    embedField = StringField(primary_key=True)
    varField = StringField()
    
    def __eq__(self, other):
        if hasattr(self, 'embedField') and hasattr(other, 'embedField'):
            return self.embedField == other.embedField
        return False


class TestDoc(Document):
#    id_field = ObjectId()
    myField = StringField()
#    secondField = StringField()
    embed_list = ListField(EmbeddedDocumentField(MyEmbed))
    
    
    
class TestDoc2(Document):
    name = StringField()
    friends = ListField(StringField())
    address_book = DictField()
    version = IntField()

  
#  OPTIONAL FIELDS AFTER ELIMINATED FOR CLEANING PURPOSES:

############# SUBMISSION ############################
#_id = ObjectIdField(required=False, primary_key=True)
    #_id = ObjectIdField()
   
#    meta = {
#        'pk' : '_id', 
#        'id_field' : '_id'
#    }
# 
################## STUDY: ############################
    #samples_list = ListField(ReferenceField('Sample'))
    # remove_x_and_autosomes = StringField()

################ SAMPLE: ##############################

    #study_list = ListField(ReferenceField(Study))
    
    
    # OPTIONAL:
    # sample_visibility = StringField()   # CHOICE
    # description = StringField()
    # supplier_name = StringField()
    # library_tube_id or list of library_tubes
    
#class Individual(DynamicEmbeddedDocument):
#    # one Indiv to many samples
#    gender = StringField()
#    cohort = StringField()
#    ethnicity = StringField()
#    individual_geographical_region = StringField()
#    organism = StringField()
#    common_name = StringField()
#    

    #samples_list = ListField(ReferenceField(Sample))
    
    # OPTIONAL:
    # individual_name = StringField()
    # country_of_origin = StringField()
    # taxon_id = StringField()
    # mother = StringField()
    # father = StringField()
    # common_name = StringField()
    
    
##################### LIBRARY ##########################
   
    # OPTIONAL:
    #sample_internal_id = IntField()    # a library is tight to a specific sample
    
  
################### SUBMITTED FILE #####################
#    individuals_list = ListField(EmbeddedDocumentField(Individual))
    #lane_list = ListField(Lane)
    #size = IntField()
    
    #file_header_mdata_status = StringField(choices=FILE_HEADER_MDATA_STATUS)
    #file_header_mdata_seqsc_status = StringField(choices=FILE_MDATA_STATUS)

  
#
#class BAMFileBatch(FileBatch):
#    experiment_id = StringField
#    
#class VCFFileBatch(FileBatch):
#    pass    




     

# OK code for Mongo
#class VCFFile(Document):
#    name = StringField(max_length=200)
#    path = StringField(max_length=200)
#
#    def __unicode__(self):
#        return self.path+'/'+self.name



#class Metadata(Document):
#    fileType = StringField(max_length=20)