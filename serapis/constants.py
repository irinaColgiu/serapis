MDATA_ROUTING_KEY = 'mdata'
UPLOAD_EXCHANGE = 'UploadExchange'
MDATA_EXCHANGE = 'MdataExchange'
UPLOAD_QUEUE_GENERAL = 'GeneralUploadQueue'
MDATA_QUEUE = 'MdataQueue'

SEQSC_HOST = "127.0.0.1"
SEQSC_PORT = 3307
#SEQSC_PORT = 20002
SEQSC_USER = "warehouse_ro"
SEQSC_DB_NAME = "sequencescape_warehouse"


#------------------- MSG SOURCE -------------------------

INIT_SOURCE = "INIT"
PARSE_HEADER_MSG_SOURCE = "PARSE_HEADER_MSG_SOURCE"
UPLOAD_FILE_MSG_SOURCE = "UPLOAD_FILE_MSG_SOURCE"
UPDATE_MDATA_MSG_SOURCE = "UPDATE_MDATA_MSG_SOURCE"
EXTERNAL_SOURCE = "EXTERNAL_SOURCE"

# ----------------- CONSTANTS USED IN TASKS -------------
UNKNOWN_FIELD = 'unknown_field'
MAX_RETRIES = 3

# HEADER constants:
# PU header:
REGEX_PU_1 = '[0-9]{4}_[0-9]{1}#[0-9]{2}'

# ----------------- VERSION INCREMENT -------------------
FILE_VERSION_INCREMENT = 1000
SAMPLES_VERSION_INCREMENT = 100
LIBRARIES_VERSION_INCREMENT = 10
STUDIES_VERSION_INCREMENT = 1


# ----------------- UPDATE TYPE -------------------------
LIBRARY_UPDATE = 'LIBRARY_UPDATE'
SAMPLE_UPDATE = 'SAMPLE_UPDATE'
STUDY_UPDATE = 'STUDY_UPDATE'
FILE_FIELDS_UPDATE = 'FILE_FIELDS_UPDATE'


# ----------------- FILE TYPES --------------------------
BAM_FILE = "bam"
BAI_FILE = "bai"
VCF_FILE = "vcf"

VCF_FORMATS = ("VCFv4.1", "VCFv4.0")

FILE_TO_INDEX_DICT = {BAM_FILE : BAI_FILE}

INDEX_FILE = 'INDEX_FILE'
MAIN_FILE = 'MAIN_FILE'
FILE_TYPES = (INDEX_FILE, MAIN_FILE)

# -------------- NEW STATUSES ---------------------------
FINISHED_STATUS = ("SUCCESS", "FAILURE")
NOT_FINISHED_STATUS = ("PENDING", "IN_PROGRESS")

# TASKS' STATUSES
# PENDING = submitted to the queue, waiting to be picked up by a worker to be executed
# IN PROGRESS = worker is working on it
HEADER_PARSING_JOB_STATUS = ("SUCCESS", "FAILURE", "PENDING_ON_USER", "PENDING_ON_WORKER", "IN_PROGRESS")
UPDATE_MDATA_JOB_STATUS = ("SUCCESS", "FAILURE", "PENDING_ON_USER", "PENDING_ON_WORKER", "IN_PROGRESS")
FILE_UPLOAD_JOB_STATUS = ("SUCCESS", "FAILURE", "PENDING_ON_USER", "PENDING_ON_WORKER", "IN_PROGRESS")

FILE_MDATA_STATUS = ("COMPLETE", "INCOMPLETE", "HAS_MINIMAL", "NOT_ENOUGH_METADATA", "IN_PROGRESS", "CONFLICT")

FILE_SUBMISSION_STATUS = ("SUCCESS", "FAILURE", "PENDING_ON_USER", "PENDING_ON_WORKER", "IN_PROGRESS",  "READY_FOR_SUBMISSION_STATUS", "SUBMITTED_TO_IRODS_STATUS")

# Defining status strings:
SUCCESS_STATUS = "SUCCESS"
FAILURE_STATUS = "FAILURE"

#PENDING_ON_CONTROLLER = "PENDING_ON_CONTROLLER"
MDATA_CONFLICT_STATUS = "CONFLICT"
PENDING_ON_USER_STATUS = "PENDING_ON_USER"
PENDING_ON_WORKER_STATUS = "PENDING_ON_WORKER"
IN_PROGRESS_STATUS = "IN_PROGRESS"
NOT_ENOUGH_METADATA_STATUS = "NOT_ENOUGH_METADATA"
READY_FOR_SUBMISSION_STATUS = "READY_FOR_SUBMISSION"
SUBMITTED_TO_IRODS_STATUS = "SUBMITTED_TO_IRODS"

COMPLETE_STATUS = "COMPLETE"
#INCOMPLETE_STATUS = "INCOMPLETE"
HAS_MINIMAL_STATUS = "HAS_MINIMAL"

# -------------- UPDATING STRATEGIES: ----------------
#KEEP_NEW = "KEEP_NEW"
#IDEMPOTENT_RAISE_CONFLICT = "IDEMPOTENT"
#KEEP_OLD = "KEEP_OLD"


# UPLOAD TASK
DEST_DIR_IRODS = "/home/ic4/tmp/serapis_staging_area/"

#-------- EVENT TYPE -------
UPDATE_EVENT = 'task-update'

# event states:

#
# ENTITY_TYPES 
LIBRARY_TYPE = 'library'
SAMPLE_TYPE = 'sample'
STUDY_TYPE = 'study'

#OTHER TYPES:
SUBMISSION_TYPE = 'submission'

#----------------------- ERROR CODES: ----------------------
IO_ERROR = "IO_ERROR"
UNEQUAL_MD5 = "UNEQUAL_MD5"
FILE_HEADER_INVALID_OR_CANNOT_BE_PARSED = "FILE HEADER INVALID OR COULD NOT BE PARSED"
FILE_HEADER_EMPTY = "FILE_HEADER_EMPTY" 
RESOURCE_NOT_UNIQUELY_IDENTIFIABLE_SEQSCAPE = "RESOURCE_NOT_UNIQUELY_IDENTIFYABLE_IN_SEQSCAPE"
PERMISSION_DENIED = "PERMISSION_DENIED"
NOT_SUPPORTED_FILE_TYPE = "NOT_SUPPORTED_FILE_TYPE"
NON_EXISTING_FILES = "NON_EXISTING_FILES"
INDEX_OLDER_THAN_FILE = "INDEX_OLDER_THAN_FILE"
UNMATCHED_INDEX_FILES = "UNMATCHED_INDEX_FILES"

PREDEFINED_ERRORS = {IO_ERROR, 
                     UNEQUAL_MD5, 
                     FILE_HEADER_INVALID_OR_CANNOT_BE_PARSED, 
                     FILE_HEADER_EMPTY, 
                     RESOURCE_NOT_UNIQUELY_IDENTIFIABLE_SEQSCAPE, 
                     PERMISSION_DENIED,
                     NOT_SUPPORTED_FILE_TYPE,
                     NON_EXISTING_FILES,
                     INDEX_OLDER_THAN_FILE,
                     UNMATCHED_INDEX_FILES
                     }

#PREDEFINED_ERRORS = {1 : 'IO ERROR COPYING FILE',
#              2 : 'MD5 DIFFERENT',
#              3 : 'FILE HEADER INVALID OR COULD NOT BE PARSED',
#              4 : 'FILE HEADER EMPTY',
#              5 : 'RESOURCE NOT UNIQUELY IDENTIFYABLE IN SEQSCAPE',
#              6 : 'PERMISSION_DENIED'
#              }

#----------------------------- SEQSCAPE TABLES: ----------------------
CURRENT_WELLS_SEQSC_TABLE = "current_wells"



