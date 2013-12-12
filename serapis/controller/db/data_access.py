

import abc
import logging
from bson.objectid import ObjectId
from serapis.com import constants, utils
from serapis.controller import models, exceptions
from mongoengine.queryset import DoesNotExist
    
class Builder:
    __metaclass__ = abc.ABCMeta
    
    @abc.abstractmethod
    def build(self, type):    
        return
    

    
class FileBuilder(object):
    __metaclass__ = abc.ABCMeta
    
#    @abc.abstractproperty
#    def model_class(self):
#        ''' This property holds the class(type) of the actual file. 
#            It must be one of the classes in models module.'''
#        return

    @classmethod
    @abc.abstractmethod
    def get_file_instance(cls, file_path):
        return
    
    
    @classmethod
    def initialize(cls, file_obj, submission):
        file_obj.submission_id = str(submission.id)
        file_obj.hgi_project_list = submission.hgi_project_list
        file_obj.irods_coll = submission.irods_collection
        
        
        # NOTE:this implementation is a all-or-nothing => either all files are uploaded as serapis or all as other user...pb?
#        if upld_as_serapis == True:
#            file_status = constants.PENDING_ON_WORKER_STATUS
#        else:
#            file_status = constants.PENDING_ON_USER_STATUS
#        
#        # Instantiating the SubmittedFile object if the file is alright
#        file_submitted.file_submission_status = file_status
#        file_submitted.file_mdata_status = file_status
        
        file_obj.file_type = submission.file_type
            
        # Set mdata from submission:
        if submission.study:
            file_obj.study_list = [submission.study]
        if submission.abstract_library:
            file_obj.abstract_library = submission.abstract_library
        if submission.file_reference_genome_id:
            file_obj.file_reference_genome_id = submission.file_reference_genome_id
        if submission.data_type:
            file_obj.data_type = submission.data_type
        if submission.data_subtype_tags:
            file_obj.data_subtype_tags = submission.data_subtype_tags
        
    
    @classmethod
    def build_index(cls, index_file_path, irods_coll):
        index_file = models.IndexFile()
        index_file.file_path_client=index_file_path
        index_file.irods_coll = irods_coll
        return index_file
    
    @classmethod
    def build(cls, file_path, index_file_path, submission):
        new_file = cls.get_file_instance(file_path)
        cls.initialize(new_file, submission)
        new_file.index_file = cls.build_index(index_file_path, submission.irods_collection)
        return new_file
        
        
    
class BAMFileBuilder(FileBuilder):
  
    @classmethod
    def get_file_instance(cls, file_path):
        return models.BAMFile(file_path_client=file_path)
    
    
#    @classmethod
#    def build(file_path, index_file_path, submission):
#        bam_file = models.BAMFile(file_path_client=file_path)
#        BAMFileBuilder.initialize(bam_file, submission)
#        bam_file.index_file = BAMFileBuilder.build_index(index_file_path, submission.irods_collection)
#        return bam_file
    
    
        
class VCFFileBuilder(FileBuilder):
    @property
    def model_class(self):
        ''' This property holds a models.VCFFile class. It is a field holding a type.'''
        return models.VCFFile
#    
#    @classmethod
#    def build(file_path, index_file_path, submission):
#        vcf_file = models.VCFFile(file_path_client=file_path)
#        VCFFileBuilder.initialize(vcf_file, submission)
#        vcf_file.index_file = VCFFileBuilder.build_index(index_file_path, submission.irods_collection)
#        return vcf_file
#    
    
class SubmissionBuilder(Builder):
    
    @classmethod
    def initialize(cls, submission, user_id, submission_data):
        submission.sanger_user_id = user_id
        submission.submission_date = utils.get_today_date()
        return submission
    
    @classmethod
    def build_and_save(cls, submission_data, user_id):
        submission = models.Submission()
        cls.initialize(submission, user_id, submission_data)
        submission.save()
        print "submission id:::::::::::;", submission.id
        if SubmissionDataAccess.update_submission(submission_data, submission.id, submission) == 1:
            return submission.id
        submission.delete()
        return None
    
    
class DataAccess(object):
    pass


class SubmissionDataAccess(DataAccess):
    
    @classmethod
    def build_submission_update_dict(cls, update_dict, submission):
        update_db_dict = dict()
        for (field_name, field_val) in update_dict.iteritems():
            if field_name == 'files_list':
                pass
            elif field_name == 'hgi_project_list' and field_val:
                for prj in field_val:
                    if not utils.is_hgi_project(prj):
                        raise ValueError("This project name is not according to HGI_project rules -- "+str(constants.REGEX_HGI_PROJECT))
                if getattr(submission, 'hgi_project_list'):
                    hgi_projects = submission.hgi_project_list
                    hgi_projects.extend(field_val)
                else:
                    hgi_projects = field_val
                update_db_dict['set__hgi_project_list'] = hgi_projects
            elif field_name == 'upload_as_serapis' and field_val:
                update_db_dict['set__upload_as_serapis'] = field_val
            # File-related metadata:
            elif field_name == 'data_subtype_tags':
                if getattr(submission, 'data_subtype_tags'):
                    subtypes_dict = submission.data_subtype_tags
                    subtypes_dict.update(field_val)
                else:
                    subtypes_dict = field_val
                update_db_dict['set__data_subtype_tags'] = subtypes_dict
            elif field_name == 'data_type':
                update_db_dict['set__data_type'] = field_val
            # TODO: put here the logic around inserting a ref genome
            elif field_name == 'file_reference_genome_id':
                models.ReferenceGenome.objects(md5=field_val).get()    # Check that the id exists in the RefGenome coll, throw exc
                update_db_dict['set__file_reference_genome_id'] = field_val
            # This should be tested if it's ok...
            elif field_name == 'library_metadata':
                update_db_dict['set__abstract_library'] = field_val
            elif field_name == 'study':
                update_db_dict['set__study'] = field_val
            elif field_name == 'irods_collection':
                update_db_dict['set__irods_collection'] = field_val
            elif field_name == 'file_type':
                update_db_dict['set__file_type'] = field_val
            else:
                logging.error("ERROR: KEY not in Submission class declaration!!!!! %s", field_name)
        return update_db_dict
        
    
    @classmethod
    def update_submission(cls, update_dict, submission_id, submission=None, nr_retries=constants.MAX_DBUPDATE_RETRIES):
        ''' Updates an existing submission or creates a new submission 
            if no submission_id is provided. 
            Returns -- 0 if nothing was changed, 1 if the update has happened
            Throws:
                ValueError - if the data in update_dict is not correct
            '''
        if submission_id == None:
            return 0
        elif not submission:
            submission = cls.retrieve_submission(submission_id)
        i, upd = 0, 0
        while i < nr_retries and upd == 0:
            update_db_dict = cls.build_submission_update_dict(update_dict, submission)
            upd = models.Submission.objects(id=submission.id, version=submission.version).update_one(**update_db_dict)
            logging.info("Updating submission...updated? %s", upd)
            i+=1
        return upd
            
    @classmethod      
    def insert_submission(cls, submission_data, user_id):
        ''' Inserts a submission in the DB, but the submission
            won't have the files_list set, as the files are created
            after the submission exists.
        '''
        submission = models.Submission()
        submission.sanger_user_id = user_id
        submission.submission_date = utils.get_today_date()
        submission.save()
        if cls.update_submission(submission_data, submission.id, submission) == 1:
            return submission.id
        submission.delete()
        return None
            
    @classmethod
    def insert_submission_date(cls, submission_id, date):
        if date != None:
            return models.Submission.objects(id=submission_id).update_one(set__submission_date=date)
        return None
    
        
    # !!! This is not ATOMIC!!!!
    @classmethod
    def delete_submission(cls, submission_id, submission=None):
        if not submission:
            submission = cls.retrieve_submission(submission_id)
        # 1. Check that all the files can be deleted:
        for file_id in submission.files_list:
            subm_file = cls.retrieve_submitted_file(file_id)
            #### if subm_file != None:
            cls.check_and_update_all_file_statuses(None, subm_file)
            if subm_file.file_submission_status in [constants.SUCCESS_STATUS, constants.IN_PROGRESS_STATUS]:
                return False
            
        # 2. Delete the files and the submission 
        models.Submission.objects(id=submission_id).delete()
        for file_id in submission.files_list:
            cls.delete_submitted_file(file_id)
        return True
    
    @classmethod
    def update_submission_file_list(cls, submission_id, files_list, submission=None):
        if not submission:
            submission = cls.retrieve_submission(submission_id)
        if not files_list:
            return cls.delete_submission(submission_id, submission)
        upd_dict = {"inc__version" : 1, "set__files_list" : files_list}
        return models.Submission.objects(id=submission_id).update_one(**upd_dict)
    
    @classmethod
    def retrieve_all_user_submissions(cls, user_id):
        return models.Submission.objects.filter(sanger_user_id=user_id)
    
    @classmethod
    def retrieve_submission(cls, subm_id):
        return models.Submission.objects(_id=ObjectId(subm_id)).get()
    
    @classmethod
    def retrieve_all_file_ids_for_submission(cls, subm_id):
        return models.Submission.objects(id=ObjectId(subm_id)).only('files_list').get().files_list
    
    @classmethod
    def retrieve_all_files_for_submission(cls, subm_id):
        files = models.SubmittedFile.objects(submission_id=subm_id)
        return [f for f in files]

    
    @classmethod    
    def retrieve_submission_date(cls, file_id, submission_id=None):
        if submission_id == None:
            submission_id = FileDataAccess.retrieve_submission_id(file_id)
        return models.Submission.objects(id=ObjectId(submission_id)).only('submission_date').get().submission_date
    
    
    # TODO: if no obj can be found => get() throws an ugly exception!
    @classmethod
    def retrieve_submission_upload_as_serapis_flag(cls, submission_id):
        if not submission_id:
            return None
        return models.Submission.objects(id=submission_id).only('upload_as_serapis').get().upload_as_serapis

    @classmethod
    def retrieve_only_submission_fields(cls, submission_id, fields_list):
        if not submission_id:
            return None
        for field in fields_list:
            if not field in models.Submission._fields:
                raise ValueError(message="Not all fields given as parameter exist as fields of a Submission type.") 
        return models.Submission.objects(id=ObjectId(submission_id)).only(*fields_list).get()

    
class FileDataAccess(DataAccess):
    
    @classmethod
    def check_if_entities_are_equal(cls, entity, json_entity):
        ''' Checks if an entity and a json_entity are equal.
            Returns boolean.
        '''
        for id_field in constants.ENTITY_IDENTITYING_FIELDS:
            if id_field in json_entity and json_entity[id_field] != None and hasattr(entity, id_field) and getattr(entity, id_field) != None:
                are_same = json_entity[id_field] == getattr(entity, id_field)
                return are_same
        return False
    
    @classmethod
    def check_if_JSONEntity_has_identifying_fields(cls, json_entity):
        ''' Entities to be inserted in the DB MUST have at least one of the uniquely
            identifying fields that are defined in ENTITY_IDENTIFYING_FIELDS list.
            If an entity doesn't contain any of these fields, then it won't be 
            inserted in the database, as it would be confusing to have entities
            that only have one insignificant field lying around and this could 
            lead to entities added multiple times in the DB.
        '''
        for identifying_field in constants.ENTITY_IDENTITYING_FIELDS:
            if json_entity.has_key(identifying_field):
                return True
        return False
    
    @classmethod
    def json2entity(cls, json_obj, source, entity_type):
        ''' Makes an entity of one of the types (entity_type param): 
            models.Entity : Library, Study, Sample 
            from the json object received as a parameter. 
            Initializes the entity fields depending on the source's priority.'''
        if not entity_type in [models.Library, models.Sample, models.Study]:
            return None
        has_identifying_fields = cls.check_if_JSONEntity_has_identifying_fields(json_obj)
        if not has_identifying_fields:
            raise exceptions.NoEntityIdentifyingFieldsProvided("No identifying fields for this entity have been given. Please provide either name or internal_id.")
        ent = entity_type()
        has_new_field = False
        for key in json_obj:
            if key in entity_type._fields  and key not in constants.ENTITY_META_FIELDS and key != None:
                setattr(ent, key, json_obj[key])
                ent.last_updates_source[key] = source
                has_new_field = True
        if has_new_field:
            return ent
        else:
            return None
        
    @classmethod    
    def json2library(cls, json_obj, source):
        return cls.json2entity(json_obj, source, models.Library)   
        
    @classmethod
    def json2study(cls, json_obj, source):
        return cls.json2entity(json_obj, source, models.Study)
    
    @classmethod
    def json2sample(cls, json_obj, source):
        return cls.json2entity(json_obj, source, models.Sample)
    
    @classmethod
    def get_entity_by_field(cls, field_name, field_value, entity_list):
        ''' Retrieves the entity that has the field given as param equal
            with the field value given as param. Returns None if no entity
            with this property is found.
        '''
        for ent in entity_list:
            if hasattr(ent, field_name):
                if getattr(ent, field_name) == field_value:
                    return ent
        return None
    
    @classmethod
    def update_entity(cls, entity_json, crt_ent, sender):
        has_changed = False
        for key in entity_json:
            old_val = getattr(crt_ent, key)
            if key in constants.ENTITY_META_FIELDS or key == None:
                continue
            elif old_val == None or old_val == 'unspecified':
                setattr(crt_ent, key, entity_json[key])
                crt_ent.last_updates_source[key] = sender
                has_changed = True
                continue
            else:
                if hasattr(crt_ent, key) and entity_json[key] == getattr(crt_ent, key):
                    continue
                if key not in crt_ent.last_updates_source:
                    crt_ent.last_updates_source[key] = constants.INIT_SOURCE
                priority_comparison = utils.compare_sender_priority(crt_ent.last_updates_source[key], sender)
                if priority_comparison >= 0:
                    setattr(crt_ent, key, entity_json[key])
                    crt_ent.last_updates_source[key] = sender
                    has_changed = True
        return has_changed
    
    
    @classmethod
    def check_if_list_has_new_entities(cls, old_entity_list, new_entity_list):
        ''' old_entity_list = list of entity objects
            new_entity_list = json list of entities
        '''
        if len(new_entity_list) == 0:
            return False
        if len(old_entity_list) == 0 and len(new_entity_list) > 0:
            return True
        for new_json_entity in new_entity_list:
            found = False
            for old_entity in old_entity_list:
                if cls.check_if_entities_are_equal(old_entity, new_json_entity):
                    found = True
            if not found:
                return True
        return False

    
    @classmethod
    def retrieve_submitted_file(cls, file_id):
        return models.SubmittedFile.objects(_id=ObjectId(file_id)).get()
        
    @classmethod
    def retrieve_sample_list(cls, file_id):
        return models.SubmittedFile.objects(id=ObjectId(file_id)).only('sample_list').get().sample_list
    
    @classmethod
    def retrieve_library_list(cls, file_id):
        return models.SubmittedFile.objects(id=ObjectId(file_id)).only('library_list').get().library_list
    
    @classmethod
    def retrieve_study_list(cls, file_id):
        return models.SubmittedFile.objects(id=ObjectId(file_id)).only('study_list').get().study_list
    
    @classmethod
    def retrieve_version(cls, file_id):
        ''' Returns the list of versions for this file (e.g. [9,1,0,1]).'''
        return models.SubmittedFile.objects(id=ObjectId(file_id)).only('version').get().version
    
    @classmethod
    def retrieve_SFile_fields_only(cls, file_id, list_of_field_names):
        ''' Returns a SubmittedFile object which has only the mentioned fields
            retrieved from DB - from efficiency reasons. The rest of the fields
            are set to None or default values.'''
        return models.SubmittedFile.objects(id=ObjectId(file_id)).only(*list_of_field_names).get()
    
    @classmethod
    def retrieve_sample_by_name(cls, sample_name, file_id, submitted_file=None):
        if submitted_file == None:
            sample_list = cls.retrieve_sample_list(file_id)
        return cls.get_entity_by_field('name', sample_name, sample_list)
    
    @classmethod
    def retrieve_library_by_name(cls, lib_name, file_id, submitted_file=None):
        if submitted_file == None:
            library_list = cls.retrieve_library_list(file_id)
        return cls.get_entity_by_field('name', lib_name, library_list)
    
    @classmethod
    def retrieve_study_by_name(cls, study_name, file_id, submitted_file=None):
        if submitted_file == None:
            study_list = cls.retrieve_study_list(file_id)
        return cls.get_entity_by_field('name', study_name, study_list)
    
    @classmethod    
    def retrieve_sample_by_id(cls, sample_id, file_id, submitted_file=None):
        if submitted_file == None:
            sample_list = cls.retrieve_sample_list(file_id)
        return cls.get_entity_by_field('internal_id', int(sample_id), sample_list)
    
    @classmethod
    def retrieve_library_by_id(cls, lib_id, file_id, submitted_file=None):
        if submitted_file == None:
            library_list = cls.retrieve_library_list(file_id)
        return cls.get_entity_by_field('internal_id', int(lib_id), library_list)
    
    @classmethod
    def retrieve_study_by_id(cls, study_id, file_id, submitted_file=None):
        if submitted_file == None:
            study_list = cls.retrieve_study_list(file_id)
        return cls.get_entity_by_field('internal_id', study_id, study_list)
    
    @classmethod
    def retrieve_submission_id(cls, file_id):
        return models.SubmittedFile.objects(id=ObjectId(file_id)).only('submission_id').get().submission_id
    
    @classmethod
    def retrieve_sanger_user_id(cls, file_id):
        #subm_id = models.SubmittedFile.objects(id=ObjectId(file_id)).only('submission_id').get().submission_id
        subm_id = cls.retrieve_submission_id(file_id)
        return models.Submission.objects(id=ObjectId(subm_id)).only('sanger_user_id').get().sanger_user_id
     
    @classmethod
    def retrieve_client_file_path(cls, file_id):
        return models.SubmittedFile.objects(id=file_id).only('file_path_client').get().file_path_client
     
    @classmethod
    def retrieve_file_md5(cls, file_id):
        return models.SubmittedFile.objects(id=file_id).only('md5').get().md5
    
    @classmethod
    def retrieve_index_md5(cls, file_id):
        return models.SubmittedFile.objects(id=file_id).only('index_file_md5').get().index_file_md5
    
    @classmethod    
    def retrieve_tasks_dict(cls, file_id):
        return models.SubmittedFile.objects(id=file_id).only('tasks_dict').get().tasks_dict
    
            
        
    #################### AUXILIARY FUNCTIONS - RELATED TO FILE VERSION ############
    
    @classmethod        
    def get_file_version(cls, file_id, submitted_file=None):
        if submitted_file == None:
            version = cls.retrieve_version(file_id)
            return version[0]
        return submitted_file.version[0]
    
    @classmethod
    def get_sample_version(cls, file_id, submitted_file=None):
        if submitted_file == None:
            version = cls.retrieve_version(file_id)
            return version[1]
        return submitted_file.version[1]
    
    @classmethod
    def get_library_version(cls, file_id, submitted_file=None):
        if submitted_file == None:
            version = cls.retrieve_version(file_id)
            return version[2]
        return submitted_file.version[2]
     
    @classmethod
    def get_study_version(cls, file_id, submitted_file=None):
        if submitted_file == None:
            version = cls.retrieve_version(file_id)
            return version[3]
        return submitted_file.version[3]
    
    
    
    
    #------------------------ SEARCH ENTITY ---------------------------------
    
    
    @classmethod
    def search_JSONEntity_in_list(cls, entity_json, entity_list):
        ''' Searches for the JSON entity within the entity list.
        Returns:
            - the entity if it was found
            - None if not
        Throws:
            exceptions.NoEntityIdentifyingFieldsProvided -- if the entity_json doesn't contain
                                                            any field to identify it.
        '''
        if entity_list == None or len(entity_list) == 0:
            return None
        has_ids = cls.check_if_JSONEntity_has_identifying_fields(entity_json)     # This throws an exception if the json entity doesn't have any ids
        if not has_ids:
            raise exceptions.NoEntityIdentifyingFieldsProvided(faulty_expression=entity_json)
        for ent in entity_list:
            if cls.check_if_entities_are_equal(ent, entity_json) == True:
                return ent
        return None
    
    @classmethod
    def search_JSONLibrary_in_list(cls, lib_json, lib_list):
        return cls.search_JSONEntity_in_list(lib_json, lib_list)
    
    @classmethod
    def search_JSONSample_in_list(cls, sample_json, sample_list):
        return cls.search_JSONEntity_in_list(sample_json, sample_list)
    
    @classmethod
    def search_JSONStudy_in_list(cls, study_json, study_list):
        return cls.search_JSONEntity_in_list(study_json, study_list)
    
    @classmethod
    def search_JSONLibrary(cls, lib_json, file_id, submitted_file=None):
        if submitted_file == None:
            submitted_file = cls.retrieve_submitted_file(file_id)
        return cls.search_JSONEntity_in_list(lib_json, submitted_file.library_list)
    
    @classmethod
    def search_JSONSample(cls, sample_json, file_id, submitted_file=None):
        if submitted_file == None:
            submitted_file = cls.retrieve_submitted_file(file_id)
        return cls.search_JSONEntity_in_list(sample_json, submitted_file.sample_list)
    
    @classmethod
    def search_JSONStudy(cls, study_json, file_id, submitted_file=None):
        if submitted_file == None:
            submitted_file = cls.retrieve_submitted_file(file_id)
        return cls.search_JSONEntity_in_list(study_json, submitted_file.study_list)
    
    
    
    
    # ------------------------ INSERTS & UPDATES -----------------------------
    
    
    # Hackish way of putting the attributes of the abstract lib, in each lib inserted:
    @classmethod
    def __update_lib_from_abstract_lib__(cls, library, abstract_lib):
        if not library:
            return None
        for field in models.AbstractLibrary._fields:
            if hasattr(abstract_lib, field) and getattr(abstract_lib, field) not in [None, "unspecified"]:
                setattr(library, field, getattr(abstract_lib, field))
        return library
        
    @classmethod
    def insert_library_in_SFObj(cls, library_json, sender, submitted_file):
        if submitted_file == None or not library_json:
            return False
        if cls.search_JSONLibrary(library_json, submitted_file.id, submitted_file) == None:
            library = cls.json2library(library_json, sender)
            library = cls.__update_lib_from_abstract_lib__(library, submitted_file.abstract_library)
            submitted_file.library_list.append(library)
            return True
        return False
    
    @classmethod
    def insert_sample_in_SFObj(cls, sample_json, sender, submitted_file):
        if submitted_file == None:
            return False
        if cls.search_JSONSample(sample_json, submitted_file.id, submitted_file) == None:
            sample = cls.json2sample(sample_json, sender)
            submitted_file.sample_list.append(sample)
            return True
        return False
    
    @classmethod
    def insert_study_in_SFObj(cls, study_json, sender, submitted_file):
        if submitted_file == None:
            return False
        if cls.search_JSONStudy(study_json, submitted_file.id, submitted_file) == None:
            study = cls.json2study(study_json, sender)
            submitted_file.study_list.append(study)
            return True
        return False
    
    @classmethod
    def insert_library_in_db(cls, library_json, sender, file_id):
        submitted_file = cls.retrieve_submitted_file(file_id)
        inserted = cls.insert_library_in_SFObj(library_json, sender, submitted_file)
        if inserted == True:
            library_version = cls.get_library_version(submitted_file.id, submitted_file)
            return models.SubmittedFile.objects(id=file_id, version__2=library_version).update_one(inc__version__2=1, inc__version__0=1, set__library_list=submitted_file.library_list)
        return 0
    
    @classmethod
    def insert_sample_in_db(cls, sample_json, sender, file_id):
        ''' Inserts in the DB the updated document with the new 
            sample inserted in the sample list.
        Returns:
            1 -- if the insert in the DB was successfully
            0 -- if not
        '''
        submitted_file = cls.retrieve_submitted_file(file_id)
        inserted = cls.insert_sample_in_SFObj(sample_json, sender, submitted_file)
        if inserted == True:
            sample_version = cls.get_sample_version(submitted_file.id, submitted_file)
            return models.SubmittedFile.objects(id=file_id, version__1=sample_version).update_one(inc__version__1=1, inc__version__0=1, set__sample_list=submitted_file.sample_list)
        return 0
    
    @classmethod
    def insert_study_in_db(cls, study_json, sender, file_id):
        submitted_file = cls.retrieve_submitted_file(file_id)
        inserted = cls.insert_study_in_SFObj(study_json, sender, submitted_file)
        logging.info("IN STUDY INSERT --> HAS THE STUDY BEEN INSERTED? %s", inserted)
        #print "HAS THE STUDY BEEN INSERTED????==============", inserted
        if inserted == True:
            study_version = cls.get_study_version(submitted_file.id, submitted_file)
            return models.SubmittedFile.objects(id=file_id, version__3=study_version).update_one(inc__version__3=1, inc__version__0=1, set__study_list=submitted_file.study_list)
        return 0
    
    
    #---------------------------------------------------------------
    @classmethod
    def update_library_in_SFObj(cls, library_json, sender, submitted_file):
        if submitted_file == None:
            return False
        crt_library = cls.search_JSONEntity_in_list(library_json, submitted_file.library_list)
        if crt_library == None:
            raise exceptions.ResourceNotFoundError(library_json)
            #return False
        return cls.update_entity(library_json, crt_library, sender)
    
    @classmethod
    def update_sample_in_SFObj(cls, sample_json, sender, submitted_file):
        if submitted_file == None:
            return False
        crt_sample = cls.search_JSONEntity_in_list(sample_json, submitted_file.sample_list)
        if crt_sample == None:
            raise exceptions.ResourceNotFoundError(sample_json)
            #return False
        return cls.update_entity(sample_json, crt_sample, sender)
    
    @classmethod
    def update_study_in_SFObj(cls, study_json, sender, submitted_file):
        if submitted_file == None:
            return False
        crt_study = cls.search_JSONEntity_in_list(study_json, submitted_file.study_list)
        if crt_study == None:
            raise exceptions.ResourceNotFoundError(study_json)
            #return False
        return cls.update_entity(study_json, crt_study, sender)
    
    
    #---------------------------------------------------------------
    
    @classmethod
    def update_library_in_db(cls, library_json, sender, file_id, library_id=None):
        ''' Throws:
                - DoesNotExist exception -- if the file being queried does not exist in the DB
                - exceptions.NoEntityIdentifyingFieldsProvided -- if the library_id isn't provided
                                                              neither as a parameter, nor in the library_json
        '''
        if library_id == None and cls.check_if_JSONEntity_has_identifying_fields(library_json) == False:
            raise exceptions.NoEntityIdentifyingFieldsProvided()
        submitted_file = cls.retrieve_submitted_file(file_id)
        if library_id != None:
            library_json['internal_id'] = int(library_id)
        has_changed = cls.update_library_in_SFObj(library_json, sender, submitted_file)
        if has_changed == True:
            lib_list_version = cls.get_library_version(submitted_file.id, submitted_file)
            return models.SubmittedFile.objects(id=file_id, version__2=lib_list_version).update_one(inc__version__2=1, inc__version__0=1, set__library_list=submitted_file.library_list)
        return 0
        
    @classmethod
    def update_sample_in_db(cls, sample_json, sender, file_id, sample_id=None):
        ''' Updates the metadata for a sample in the DB. 
        Throws:
            - DoesNotExist exception -- if the file being queried does not exist in the DB
            - exceptions.NoEntityIdentifyingFieldsProvided -- if the sample_id isn't provided
                                                              neither as a parameter, nor in the sample_json
        '''
        if sample_id == None and cls.check_if_JSONEntity_has_identifying_fields(sample_json) == False:
            raise exceptions.NoEntityIdentifyingFieldsProvided()
        submitted_file = cls.retrieve_submitted_file(file_id)
        if sample_id != None:
            sample_json['internal_id'] = int(sample_id)
        has_changed = cls.update_sample_in_SFObj(sample_json, sender, submitted_file)
        if has_changed == True:
            sample_list_version = cls.get_sample_version(submitted_file.id, submitted_file)
            return models.SubmittedFile.objects(id=file_id, version__1=sample_list_version).update_one(inc__version__1=1, inc__version__0=1, set__sample_list=submitted_file.sample_list)
        return 0
    
    @classmethod
    def update_study_in_db(cls, study_json, sender, file_id, study_id=None):
        ''' Throws:
                - DoesNotExist exception -- if the file being queried does not exist in the DB
                - exceptions.NoEntityIdentifyingFieldsProvided -- if the study_id isn't provided
                                                                  neither as a parameter, nor in the study_json            
        '''
        if study_id == None and cls.check_if_JSONEntity_has_identifying_fields(study_json) == False:
            raise exceptions.NoEntityIdentifyingFieldsProvided()
        submitted_file = cls.retrieve_submitted_file(file_id)
        if study_id != None:
            study_json['internal_id'] = int(study_id)
        has_changed = cls.update_study_in_SFObj(study_json, sender, submitted_file)
        if has_changed == True:
            lib_list_version = cls.get_study_version(submitted_file.id, submitted_file)
            return models.SubmittedFile.objects(id=file_id, version__3=lib_list_version).update_one(inc__version__3=1, inc__version__0=1, set__study_list=submitted_file.study_list)
        return 0
    
       
    #------------------------------------------------------------------------------------
    
    @classmethod
    def insert_or_update_library_in_SFObj(cls, library_json, sender, submitted_file):
        if submitted_file == None or library_json == None:
            return False
        lib_exists = cls.search_JSONEntity_in_list(library_json, submitted_file.library_list)
        if not lib_exists:
            return cls.insert_library_in_SFObj(library_json, sender, submitted_file)
        else:
            return cls.update_library_in_SFObj(library_json, sender, submitted_file)
    
    @classmethod   
    def insert_or_update_sample_in_SFObj(cls, sample_json, sender, submitted_file):
        if submitted_file == None or sample_json == None:
            return False
        sample_exists = cls.search_JSONEntity_in_list(sample_json, submitted_file.sample_list)
        if sample_exists == None:
            return cls.insert_sample_in_SFObj(sample_json, sender, submitted_file)
        else:
            return cls.update_sample_in_SFObj(sample_json, sender, submitted_file)
    
    @classmethod
    def insert_or_update_study_in_SFObj(cls, study_json, sender, submitted_file):
        if submitted_file == None or study_json == None:
            return False
        study_exists = cls.search_JSONEntity_in_list(study_json, submitted_file.study_list)
        if study_exists == None:
            return cls.insert_study_in_SFObj(study_json, sender, submitted_file)
        else:
            return cls.update_study_in_SFObj(study_json, sender, submitted_file)
        
    
    
    #--------------------------------------------------------------------------------
    
    @classmethod
    def insert_or_update_library_in_db(cls, library_json, sender, file_id):
        submitted_file = cls.retrieve_submitted_file(file_id)
        done = False
        lib_exists = cls.search_JSONEntity_in_list(library_json, submitted_file.library_list)
        if lib_exists == None:
            done = cls.insert_library_in_SFObj(library_json, sender, submitted_file)
        else:
            done = cls.update_library_in_SFObj(library_json, sender, submitted_file)
        if done == True:
            lib_list_version = cls.get_library_version(submitted_file.id, submitted_file)
            return models.SubmittedFile.objects(id=file_id, version__2=lib_list_version).update_one(inc__version__2=1, inc__version__0=1, set__library_list=submitted_file.library_list)
        
    @classmethod
    def insert_or_update_sample_in_db(cls, sample_json, sender, file_id):
        submitted_file = cls.retrieve_submitted_file(file_id)
        done = False
        sample_exists = cls.search_JSONEntity_in_list(sample_json, submitted_file.sample_list)
        if sample_exists == None:
            done = cls.insert_sample_in_db(sample_json, sender, file_id)
        else:
            done = cls.update_sample_in_db(sample_json, sender, file_id)
        if done == True:
            sample_list_version = cls.get_sample_version(submitted_file.id, submitted_file)
            return models.SubmittedFile.objects(id=file_id, version__1=sample_list_version).update_one(inc__version__1=1, inc__version__0=1, set__sample_list=submitted_file.sample_list) 
    
    @classmethod
    def insert_or_update_study_in_db(cls, study_json, sender, file_id):
        submitted_file = cls.retrieve_submitted_file(file_id)
    #    for old_study in submitted_file.study_list:
    #        if check_if_entities_are_equal(old_study, study_json) == True:                      #if new_entity.is_equal(old_entity):
    #            print "INSERT OR UPDATE -------------------- WAS FOUND = TRUE: study json", study_json, "  and Old study: ", old_study
        done = False
        study_exists = cls.search_JSONEntity_in_list(study_json, submitted_file.study_list)
        if study_exists == None:
            done = cls.insert_study_in_db(study_json, sender, file_id)
        else:
            done = cls.update_study_in_db(study_json, sender, file_id)
        if done == True:
            study_list_version = cls.get_study_version(submitted_file.id, submitted_file)
            return models.SubmittedFile.objects(id=file_id, version__3=study_list_version).update_one(inc__version__3=1, inc__version__0=1, set__study_list=submitted_file.study_list) 
    
        
    
    #---------------------------------------------------------------------------------
    
    @classmethod        
    def update_library_list(cls, library_list, sender, submitted_file):
        if submitted_file == None:
            return False
        for library in library_list:
            cls.insert_or_update_library_in_SFObj(library, sender, submitted_file)
        return True
    
    @classmethod
    def update_sample_list(cls, sample_list, sender, submitted_file):
        if submitted_file == None:
            return False
        for sample in sample_list:
            cls.insert_or_update_sample_in_SFObj(sample, sender, submitted_file)
        return True
    
    @classmethod
    def update_study_list(cls, study_list, sender, submitted_file):
        if submitted_file == None:
            return False
        for study in study_list:
            cls.insert_or_update_study_in_SFObj(study, sender, submitted_file)
        return True
    
    #-------------------------------------------------------------
    
    @classmethod
    def update_and_save_library_list(cls, library_list, sender, file_id):
        if library_list == None or len(library_list) == 0:
            return False
        for library in library_list:
            upsert = cls.insert_or_update_library_in_db(library, sender, file_id)
        return True
    
    @classmethod
    def update_and_save_sample_list(cls, sample_list, sender, file_id):
        if sample_list == None or len(sample_list) == 0:
            return False
        for sample in sample_list:
            upsert = cls.insert_or_update_sample_in_db(sample, sender, file_id)
        return True
    
    @classmethod
    def update_and_save_study_list(cls, study_list, sender, file_id):
        if study_list == None or len(study_list) == 0:
            return False
        for study in study_list:
            upsert = cls.insert_or_update_study_in_db(study, sender, file_id)
        return True
    
    @classmethod
    def __upd_list_of_primary_types__(cls, crt_list, update_list_json):
        if  len(update_list_json) == 0:
            return 
        crt_set = set(crt_list)
        new_set = set(update_list_json)
        res = crt_set.union(new_set)
        crt_list = list(res)
        return crt_list
    
    
    @classmethod    
    def build_file_update_dict(cls, file_updates, update_source, file_id, submitted_file):
        update_db_dict = dict()
        for (field_name, field_val) in file_updates.iteritems():
            if field_val == 'null' or not field_val:
                pass
            if field_name in submitted_file._fields:        
                if field_name in ['submission_id', 
                             'id',
                             '_id',
                             'version',
                             'file_type', 
                             'irods_coll',      # TODO: make it updateble by user, if file not yet submitted to permanent irods coll 
                             'file_path_client', 
                             'last_updates_source', 
                             'file_mdata_status',
                             'file_submission_status',
                             'missing_mandatory_fields_dict']:
                    pass
                elif field_name == 'library_list': 
                    if len(field_val) > 0:
                        was_updated = cls.update_library_list(field_val, update_source, submitted_file)
                        update_db_dict['set__library_list'] = submitted_file.library_list
                        update_db_dict['inc__version__2'] = 1
                        #update_db_dict['inc__version__0'] = 1
                        logging.info("UPDATE  FILE TO SUBMIT --- UPDATING LIBRARY LIST.................................%s ", was_updated)
                elif field_name == 'sample_list':
                    if len(field_val) > 0:
                        was_updated = cls.update_sample_list(field_val, update_source, submitted_file)
                        update_db_dict['set__sample_list'] = submitted_file.sample_list
                        update_db_dict['inc__version__1'] = 1
                        #update_db_dict['inc__version__0'] = 1
                        logging.info("UPDATE  FILE TO SUBMIT ---UPDATING SAMPLE LIST -- was it updated? %s", was_updated)
                elif field_name == 'study_list':
                    if len(field_val) > 0:
                        was_updated = cls.update_study_list(field_val, update_source, submitted_file)
                        update_db_dict['set__study_list'] = submitted_file.study_list
                        update_db_dict['inc__version__3'] = 1
                        #update_db_dict['inc__version__0'] = 1
                        logging.info("UPDATING STUDY LIST - was it updated? %s", was_updated)
    
                # Fields that only the workers' PUT req are allowed to modify - donno how to distinguish...
                elif field_name == 'missing_entities_error_dict':
                    if field_val:
                        for entity_categ, entities in field_val.iteritems():
                            update_db_dict['add_to_set__missing_entities_error_dict__'+entity_categ] = entities
                        #update_db_dict['inc__version__0'] = 1
                elif field_name == 'not_unique_entity_error_dict':
                    if field_val:
                        for entity_categ, entities in field_val.iteritems():
                            #update_db_dict['push_all__not_unique_entity_error_dict'] = entities
                            update_db_dict['add_to_set__not_unique_entity_error_dict__'+entity_categ] = entities
                        #update_db_dict['inc__version__0'] = 1
                elif field_name == 'header_has_mdata':
                    if update_source == constants.PARSE_HEADER_TASK:
                        update_db_dict['set__header_has_mdata'] = field_val
                        #update_db_dict['inc__version__0'] = 1
                elif field_name == 'md5':
                    if update_source == constants.CALC_MD5_TASK:
                        update_db_dict['set__md5'] = field_val
                        #update_db_dict['inc__version__0'] = 1
                        logging.debug("UPDATING md5")
                elif field_name == 'index_file':
                    if update_source == constants.CALC_MD5_TASK: 
                        if 'md5' in field_val:
                            update_db_dict['set__index_file__md5'] = field_val['md5']
                            #update_db_dict['inc__version__0'] = 1
                        else:
                            raise exceptions.MdataProblem("Calc md5 task did not return a dict with an md5 field in it!!!")
                elif field_name == 'hgi_project_list':
                    if update_source == constants.EXTERNAL_SOURCE:
                        for prj in field_val:
                            if not utils.is_hgi_project(prj):
                                raise ValueError("This project name is not according to HGI_project rules -- "+str(constants.REGEX_HGI_PROJECT))
                        if getattr(submitted_file, 'hgi_project_list'):
                            hgi_projects = submitted_file.hgi_project_list
                            hgi_projects.extend(field_val)
                        else:
                            hgi_projects = field_val                    
                        update_db_dict['set__hgi_project_list'] = hgi_projects
                elif field_name == 'data_type':
                    if update_source == constants.EXTERNAL_SOURCE:
                        update_db_dict['set__data_type'] = field_val
                        #update_db_dict['inc__version__0'] = 1
                elif field_name == 'data_subtype_tags':
                    if update_source in [constants.EXTERNAL_SOURCE, constants.PARSE_HEADER_TASK]:
                        if getattr(submitted_file, 'data_subtype_tags') != None:
                            subtypes_dict = submitted_file.data_subtype_tags
                            subtypes_dict.update(field_val)
                        else:
                            subtypes_dict = field_val
                        update_db_dict['set__data_subtype_tags'] = subtypes_dict
                        #update_db_dict['inc__version__0'] = 1
                elif field_name == 'abstract_library':
                    if update_source == constants.EXTERNAL_SOURCE:
                        update_db_dict['set__abstract_library'] = field_val
                        #update_db_dict['inc__version__0'] = 1
                elif field_name == 'file_reference_genome_id':
                    if update_source == constants.EXTERNAL_SOURCE:
                        models.ReferenceGenome.objects(md5=field_val).get()    # Check that the id exists in the RefGenome coll, throw exc
                        update_db_dict['set__file_reference_genome_id'] = str(field_val)
                        #update_db_dict['inc__version__0'] = 1
                
                elif field_name != None and field_name != "null":
                    logging.info("Key in VARS+++++++++++++++++++++++++====== but not in the special list: %s", field_name)
            elif field_name == 'reference_genome':
                    ref_gen = cls.get_or_insert_reference_genome(field_val)     # field_val should be a path
                    update_db_dict['set__file_reference_genome_id'] = ref_gen.md5
            else:
                logging.error("KEY ERROR RAISED!!! KEY = %s, VALUE = %s", field_name, field_val)
                
#        file_specific_upd_dict = None
#        if submitted_file.file_type == constants.BAM_FILE:
#            file_specific_upd_dict = cls.build_bam_file_update_dict(file_updates, update_source, file_id, submitted_file)
#        elif submitted_file.file_type == constants.VCF_FILE:
#            file_specific_upd_dict = cls.build_vcf_file_update_dict(file_updates, update_source, file_id, submitted_file)
#        if file_specific_upd_dict:
#            update_db_dict.update(file_specific_upd_dict)
        return update_db_dict
    
    
    #    seq_centers = ListField()           # list of strings - List of sequencing centers where the data has been sequenced
    #    run_list = ListField()              # list of strings
    #    platform_list = ListField()         # list of strings
    #    seq_date_list = ListField()             # list of strings
    #    library_well_list = ListField()     # List of strings containing internal_ids of libs found in wells table
    #    multiplex_lib_list = ListField()    # List of multiplexed library ids
    
    
    @classmethod
    def build_vcf_file_update_dict(cls, file_updates, update_source, file_id, submitted_file):
        update_db_dict = {}
        for (field_name, field_val) in file_updates.iteritems():
            if field_val == 'null' or not field_val:
                pass
            elif field_name == 'used_samtools':
                update_db_dict['set__used_samtools'] = field_val
            elif field_name == 'file_format':
                update_db_dict['set__file_format'] = field_val
        return update_db_dict
                          
    @classmethod
    def update_file_mdata(cls, file_id, file_updates, update_source, task_id=None, task_status=None, errors=None, nr_retries=constants.MAX_DBUPDATE_RETRIES):
        upd, i = 0, 0
        db_update_dict = {}
        if task_id:
            db_update_dict = {"set__tasks_dict__"+task_id+"__status" : task_status}
            if errors:
                for e in errors:
                    db_update_dict['add_to_set__file_error_log'] = e
        while i < nr_retries:
            submitted_file = cls.retrieve_submitted_file(file_id)
            field_updates = cls.build_file_update_dict(file_updates, update_source, file_id, submitted_file)
            if field_updates:
                db_update_dict.update(field_updates)
                db_update_dict['inc__version__0'] = 1
            if len(db_update_dict) > 0:
                logging.info("UPDATE FILE TO SUBMIT - FILE ID: %s and UPD DICT: %s", str(file_id),str(db_update_dict))
                upd = models.SubmittedFile.objects(id=file_id, version__0=cls.get_file_version(submitted_file.id, submitted_file)).update_one(**db_update_dict)
                logging.info("ATOMIC UPDATE RESULT from :%s, NR TRY = %s, WAS THE FILE UPDATED? %s", update_source, i, upd)
            if upd == 1:
                break
            i+=1
        return upd
    
    @classmethod
    def update_data_subtype_tags(cls, file_id, subtype_tags_dict):
        return models.SubmittedFile.objects(id=file_id).update_one(set__data_subtype_tags=subtype_tags_dict, inc__version__0=1)

    @classmethod
    def update_file_ref_genome(cls, file_id, ref_genome_key):    # the ref genome key is the md5
        return models.SubmittedFile.objects(id=file_id).update_one(set__file_reference_genome_id=ref_genome_key, inc__version__0=1)
    
    @classmethod
    def update_file_data_type(cls, file_id, data_type):
        return models.SubmittedFile.objects(id=file_id).update_one(set__data_type=data_type, inc__version__0=1)
    
    @classmethod
    def update_file_abstract_library(cls, file_id, abstract_lib):
        return models.SubmittedFile.objects(id=file_id, abstract_library=None).update_one(set__abstract_library=abstract_lib, inc__version__0=1)
    
    @classmethod
    def update_file_submission_status(cls, file_id, status):
        upd_dict = {'set__file_submission_status' : status, 'inc__version__0' : 1}
        return models.SubmittedFile.objects(id=file_id).update_one(**upd_dict)
        
    @classmethod
    def update_file_statuses(cls, file_id, statuses_dict):
        if not statuses_dict:
            return 0
        upd_dict = dict()
        for k,v in statuses_dict.items():
            upd_dict['set__'+k] = v
        upd_dict['inc__version__0'] = 1
        return models.SubmittedFile.objects(id=file_id).update_one(**upd_dict)
    
    @classmethod
    def update_file_mdata_status(cls, file_id, status):
        upd_dict = {'set__file_mdata_status' : status, 'inc__version__0' : 1}
        return models.SubmittedFile.objects(id=file_id).update_one(**upd_dict)
    
    @classmethod
    def update_file_error_log(cls, error_log, file_id=None, submitted_file=None):
        if file_id == None and submitted_file == None:
            return None
        if submitted_file == None:
            submitted_file = cls.retrieve_submitted_file(file_id)
        old_error_log = submitted_file.file_error_log
        if type(error_log) == list:
            old_error_log.extend(error_log)
        elif type(error_log) == str or type(error_log) == unicode:
            old_error_log.append(error_log)
        logging.error("IN UPDATE ERROR LOG LIST ------------------- PRINT ERROR LOG LIST:::::::::::: %s", ' '.join(str(it) for it in error_log))
        upd_dict = {'set__file_error_log' : old_error_log, 'inc__version__0' : 1}
        return models.SubmittedFile.objects(id=submitted_file.id, version__0=cls.get_file_version(None, submitted_file)).update_one(**upd_dict)
        
    
    @classmethod
    def add_task_to_file(cls, file_id, task_id, task_type, task_status, nr_retries=constants.MAX_DBUPDATE_RETRIES):
        upd_dict = {'set__tasks_dict__'+task_id : {'type' : task_type, 'status' : task_status}, 'inc__version__0' : 1}
        upd = 0
        while nr_retries > 0 and upd == 0:
            upd = models.SubmittedFile.objects(id=file_id).update_one(**upd_dict)
            logging.info("ADDING NEW TASK TO TASKS dict %s", upd)
        return upd
    
    @classmethod
    def update_task_status(cls, file_id, task_id, task_status, errors=None, nr_retries=constants.MAX_DBUPDATE_RETRIES):
        upd_dict = {'set__tasks_dict__'+task_id+'__status' : task_status, 'inc__version__0' : 1}
        if errors:
            for e in errors:
                upd_dict['add_to_set__file_error_log'] = e
        upd = 0
        while nr_retries > 0 and upd == 0:
            upd = models.SubmittedFile.objects(id=file_id).update_one(**upd_dict)
            logging.info("UPDATING TASKS dict %s", upd)
        return upd
    
    
    
    #        - 2nd elem of the list = version of the list of samples mdata
    #        - 3rd elem of the list = version of the list of libraries mdata
    #        - 4th elem of the list = version of the list of studies mdata
    
    @classmethod
    def update_file_from_dict(cls, file_id, update_dict, update_type_list=[constants.FILE_FIELDS_UPDATE], nr_retries=constants.MAX_DBUPDATE_RETRIES):
        db_upd_dict = {}
        for upd_type in update_type_list:
            if upd_type == constants.FILE_FIELDS_UPDATE:
                db_upd_dict['inc__version__0'] = 1
            elif upd_type == constants.SAMPLE_UPDATE:
                db_upd_dict['inc__version__1'] = 1
            elif upd_type == constants.LIBRARY_UPDATE:
                db_upd_dict['inc__version__2'] = 1
            elif upd_type == constants.STUDY_UPDATE:
                db_upd_dict['inc__version__3'] = 1
            else:
                logging.error("Update file fields -- Different updates than the 4 type acccepted? %s", update_type_list)
                
        for upd_field, val in update_dict.items():
            db_upd_dict['set__'+upd_field] =  val
        upd, i = 0, 0
        while i < nr_retries and upd == 0:
            upd = models.SubmittedFile.objects(id=file_id).update_one(**db_upd_dict)
        return upd
    
    # PB: I am not keeping track of submission's version...
    # PB: I am not returning an error code/ Exception if the hgi-project name is incorrect!!!
    @classmethod
    def insert_hgi_project(cls, subm_id, project):
        if utils.is_hgi_project(project):
            upd_dict = {'add_to_set__hgi_project_list' : project}
            return models.Submission.objects(id=subm_id).update_one(**upd_dict)
    
    @classmethod
    def delete_library(cls, file_id, library_id):
        submitted_file = cls.retrieve_SFile_fields_only(file_id, ['library_list', 'version'])
        new_list = []
        found = False
        for lib in submitted_file.library_list:
            if lib.internal_id != int(library_id):
                new_list.append(lib)
            else:
                found = True
        if found == True:
            return models.SubmittedFile.objects(id=file_id, version__2=cls.get_library_version(submitted_file.id, submitted_file)).update_one(inc__version__2=1, inc__version__0=1, set__library_list=new_list)
        else:
            raise exceptions.ResourceNotFoundError(library_id)
    
    @classmethod
    def delete_sample(cls, file_id, sample_id):
        submitted_file = cls.retrieve_SFile_fields_only(file_id, ['sample_list', 'version'])
        new_list = []
        found = False
        for lib in submitted_file.sample_list:
            if lib.internal_id != int(sample_id):
                new_list.append(lib)
            else:
                found = True
        if found == True:
            return models.SubmittedFile.objects(id=file_id, version__1=cls.get_sample_version(submitted_file.id, submitted_file)).update_one(inc__version__1=1, inc__version__0=1, set__sample_list=new_list)
        else:
            raise exceptions.ResourceNotFoundError(sample_id)
    
    @classmethod
    def delete_study(cls, file_id, study_id):
        submitted_file = cls.retrieve_SFile_fields_only(file_id, ['study_list', 'version'])
        new_list = []
        found = False
        for lib in submitted_file.study_list:
            if lib.internal_id != int(study_id):
                new_list.append(lib)
            else:
                found = True
        if found == True:
            return models.SubmittedFile.objects(id=file_id, version__3=cls.get_study_version(submitted_file.id, submitted_file)).update_one(inc__version__3=1, inc__version__0=1, set__study_list=new_list)
        else:
            raise exceptions.ResourceNotFoundError(study_id)
    
    @classmethod
    def delete_submitted_file(cls, file_id, submitted_file=None):
        if submitted_file == None:
            submitted_file = models.SubmittedFile.objects(id=file_id)
        submitted_file.delete()
        return True

    
#        file_specific_upd_dict = None
#        if submitted_file.file_type == constants.BAM_FILE:
#            file_specific_upd_dict = cls.build_bam_file_update_dict(file_updates, update_source, file_id, submitted_file)
#        elif submitted_file.file_type == constants.VCF_FILE:
#            file_specific_upd_dict = cls.build_vcf_file_update_dict(file_updates, update_source, file_id, submitted_file)
#        if file_specific_upd_dict:
#            update_db_dict.update(file_specific_upd_dict)
#        return update_db_dict


class BAMFileDataAccess(FileDataAccess):
    
    @classmethod
    def build_file_update_dict(cls, file_updates, update_source, file_id, submitted_file):
        update_db_dict = super(BAMFileDataAccess, cls).build_file_update_dict(file_updates, update_source, file_id, submitted_file)
        for (field_name, field_val) in file_updates.iteritems():
            if field_val == 'null' or not field_val:
                pass
            if field_name in submitted_file._fields:        
                if field_name in ['submission_id', 
                             'id',
                             '_id',
                             'version',
                             'file_type', 
                             'irods_coll',      # TODO: make it updateble by user, if file not yet submitted to permanent irods coll 
                             'file_path_client', 
                             'last_updates_source', 
                             'file_mdata_status',
                             'file_submission_status',
                             'missing_mandatory_fields_dict']:
                    pass
                elif field_name == 'seq_centers':
                    if update_source in [constants.PARSE_HEADER_TASK, constants.EXTERNAL_SOURCE]:
                        updated_list = cls.__upd_list_of_primary_types__(submitted_file.seq_centers, field_val)
                        update_db_dict['set__seq_centers'] = updated_list
                        #update_db_dict['inc__version__0'] = 1
                elif field_name == 'run_list':
                    if update_source in [constants.PARSE_HEADER_TASK, constants.EXTERNAL_SOURCE]:
                        updated_list = cls.__upd_list_of_primary_types__(submitted_file.run_list, field_val)
                        update_db_dict['set__run_list'] = updated_list
                        #update_db_dict['inc__version__0'] = 1
                elif field_name == 'platform_list':
                    if update_source in [constants.PARSE_HEADER_TASK, constants.EXTERNAL_SOURCE]:
                        updated_list = cls.__upd_list_of_primary_types__(submitted_file.platform_list, field_val)
                        update_db_dict['set__platform_list'] = updated_list
                elif field_name == 'seq_date_list':
                    if update_source in [constants.PARSE_HEADER_TASK, constants.EXTERNAL_SOURCE]:
                        updated_list = cls.__upd_list_of_primary_types__(submitted_file.seq_date_list, field_val)
                        update_db_dict['set__seq_date_list'] = updated_list
                elif field_name == 'library_well_list':
                    if update_source in [constants.PARSE_HEADER_TASK, constants.EXTERNAL_SOURCE]:
                        updated_list = cls.__upd_list_of_primary_types__(submitted_file.library_well_list, field_val)
                        update_db_dict['set__library_well_list'] = updated_list
                elif field_name == 'multiplex_lib_list':
                    if update_source in [constants.PARSE_HEADER_TASK, constants.EXTERNAL_SOURCE]:
                        updated_list = cls.__upd_list_of_primary_types__(submitted_file.multiplex_lib_list, field_val)
                        update_db_dict['set__multiplex_lib_list'] = updated_list
        return update_db_dict
    


class VCFFileDataAccess(FileDataAccess):
    pass


class ReferenceGenomeDataAccess(DataAccess):
 
    @classmethod   
    def insert_reference_genome(cls, ref_dict):
        ref_genome = models.ReferenceGenome()
        if 'name' in ref_dict:
            #ref_name = ref_dict['name']
            ref_genome.name = ref_dict['name']
        if 'path' in ref_dict:
            ref_genome.paths = [ref_dict['path']]
        else:
            raise exceptions.NotEnoughInformationProvided(msg="You must provide both the name and the path for the reference genome.") 
        md5 = utils.calculate_md5(ref_dict['path'])
        ref_genome.md5 = md5
        ref_genome.save()
        return ref_genome
    
    #def insert_reference_genome(ref_dict):
    #    ref_genome = models.ReferenceGenome()
    #    if 'name' in ref_dict:
    #        #ref_name = ref_dict['name']
    #        ref_genome.name = ref_dict['name']
    #    if 'path' in ref_dict:
    #        if not type(ref_dict['path']) == list:
    #            ref_genome.paths = [ref_dict['path']]
    #        else:
    #            ref_genome.paths = ref_dict
    #    else:
    #        raise exceptions.NotEnoughInformationProvided(msg="You must provide both the name and the path for the reference genome.") 
    ##    ref_genome.name = ref_name
    ##    ref_genome.paths = path_list
    ##    
    #    for path in ref_genome.paths:
    #        md5 = calculate_md5(path)
    #    ref_genome.md5 = md5
    #    ref_genome.save()
    #    return ref_genome
        
    @classmethod
    def retrieve_reference_by_path(cls, path):
        try:
            return models.ReferenceGenome.objects(paths__in=[path]).hint([('paths', 1)]).get()
        except DoesNotExist:
            return None
        
    @classmethod
    def retrieve_reference_by_md5(cls, md5):
        try:
            found = models.ReferenceGenome.objects.get(pk=md5)
            return found
        except DoesNotExist:
            return None
    
    @classmethod
    def retrieve_reference_by_name(cls, canonical_name):
        try:
            return models.ReferenceGenome.objects(name=canonical_name).get()
        except DoesNotExist:
            return None
        
    @classmethod
    def retrieve_reference_genome(cls, ref_gen_dict):
        if not ref_gen_dict:
            raise exceptions.NoEntityIdentifyingFieldsProvided("No identifying fields provided")
        ref_gen_name, ref_gen_p = None, None
        if 'name' in ref_gen_dict:
            ref_gen_name = cls.retrieve_reference_by_name(ref_gen_dict['name'])
        if 'path' in ref_gen_dict:
            ref_gen_p = cls.retrieve_reference_by_path(ref_gen_dict['path'])
        
        if ref_gen_name and ref_gen_p and ref_gen_name != ref_gen_p:
            raise exceptions.InformationConflict(msg="The reference genome name "+ref_gen_dict['name'] +"and the path "+ref_gen_dict['path']+" corresponds to different entries in our DB.")
        if ref_gen_name:
            return ref_gen_name.id
        if ref_gen_p:
            return ref_gen_p.id
        return None
    
    
    @classmethod
    def get_or_insert_reference_genome(cls, file_path):
        ''' This function receives a path identifying 
            a reference file and retrieves it from the database 
            or inserts it if it's not there.
        Parameters: a path(string)
        Throws:
            - TooMuchInformationProvided exception - when the dict has more than a field
            - NotEnoughInformationProvided - when the dict is empty
        '''
        if not file_path:
            raise exceptions.NotEnoughInformationProvided(msg="ERROR: the path of the reference genome must be provided.")        
        ref_gen = cls.retrieve_reference_by_path(file_path)
        if ref_gen:
            return ref_gen
        return cls.insert_reference_genome({'path' : file_path})
        
        
    @classmethod
    def get_or_insert_reference_genome_path_and_name(cls, data):
        ''' This function receives a dictionary with data identifying 
            a reference genome and retrieves it from the data base.
        Parameters: a dictionary
        Throws:
            - TooMuchInformationProvided exception - when the dict has more than a field
            - NotEnoughInformationProvided - when the dict is empty
        '''
        if not 'name' in data and not 'path' in data:
            raise exceptions.NotEnoughInformationProvided(msg="ERROR: either the name or the path of the reference genome must be provided.")        
        ref_gen = cls.retrieve_reference_genome(data)
        if ref_gen:
            return ref_gen
        return cls.insert_reference_genome(data)
    



    
    
    