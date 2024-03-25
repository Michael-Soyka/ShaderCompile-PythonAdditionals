import os
from subprocess import run
from pathlib import Path
from re import match
from json import dumps, load
from shutil import copyfile

CONFIG_VERSION = 2.1
CONFIG_FILE = './' + '_shader_conf.json'

SHADER_LIST_FILE = './' + '_shaders_list.json'

# TODO: Add support for other langs. Thanks to a MICROSOFT devs! They change locale format!
#   >>> import locale
#   >>> locale.getlocale()              <--- NEW
#   ('English_United States', '1252')
#   >>> locale.getdefaultlocale()       <--- OLD
#   ('en_US', 'cp1252') 

# Windows cmd colors stuff
def prError(skk): print("\033[91m{}\033[00m" .format(skk))
def prSuccessful(skk): print("\033[92m{}\033[00m" .format(skk))
def prWarn(skk): print("\033[93m{}\033[00m" .format(skk))
def prBtw(skk): print("\033[97m{}\033[00m" .format(skk))
#

class cConf:
    dir_src = ''
    dir_shaders = '' 
    dir_mod = ''
    shader_compiler = ''
    threads = 0
    force_dynamic = False

    base_config = {
        "conf-version" : CONFIG_VERSION,

        "dir-src" : "G:/vance-src",
        "dir-shaders" : "G:/vance-src/shaders",
        "dir-mod" : "G:/vance-game/vance",

        "threads" : 2,

        "shader-compiler" : "devtools/bin/ShaderCompile.exe",
        "shader-force-dynamic" : False,
    }
        
    def config_write( self, config_data ):
        try:
            with open( CONFIG_FILE, mode='w', encoding='utf-8' ) as config_f:
                json_data = dumps( config_data, indent=4 )
                config_f.write( json_data )
                config_f.close()
        except IOError as ioe:
            prWarn( 'Something went wrong while saving config.\n' + ioe )
            exit( ioe )

    def config_update( self, config_data ):
        config_data[ 'conf-version' ] = CONFIG_VERSION

        if ( CONFIG_VERSION - config_data['conf-version'] ) > 5:
            if 'depricated' in config_data:
                config_data.pop( 'depricated' )

        for key, value in self.base_config.items():
            if not key in config_data:
                config_data[ key ] = value

        for key, value in list(config_data.items()):
            if not key in self.base_config:
                if not 'depricated' in config_data:
                    config_data[ 'depricated' ] = {}
                config_data[ 'depricated' ][ key ] = value
                config_data.pop( key )

        self.config_write( config_data )

    def config_create( self ):
        self.config_write( self.base_config )
        print( 'Created default config with next params:\n' + dumps( self.base_config, indent=4 ) )

    def __init__(self):
        if not Path( CONFIG_FILE ).exists():
            prWarn( 'Config file was not found, creating...' )
            self.config_create()
        else:
            print('Config file was found, loading...')

        config_json = {}
        
        try:
            with open( CONFIG_FILE, mode='r', encoding='utf-8' ) as config_f:
                config_json = load(config_f)
                config_f.close()
            prSuccessful( f'Loaded config version: {config_json['conf-version']}' )
        except IOError as ioe:
            prWarn( f'Something went wrong while trying to read config.\n' + ioe )
            exit( ioe )

        if config_json[ 'conf-version' ] != CONFIG_VERSION:
            prWarn( 'Config is outdated! Updating...' )
            self.config_update( config_json )

        self.dir_src = config_json[ "dir-src" ]
        self.dir_shaders = config_json[ "dir-shaders" ]
        self.dir_mod = config_json[ "dir-mod" ]
        self.shader_compiler = config_json[ "shader-compiler" ]
        self.threads = config_json[ "threads" ]
        self.force_dynamic = config_json[ "shader-force-dynamic" ]

def get_all_shaders_count():
    return len( list( Path.cwd().rglob( '*.fxc' ) ) )

def defineShaderVersionByName( name_shader ):
    defined_version = ''

    if match( ".+(ps|vs)2.+", name_shader ):
        defined_version = '20b'
    elif match( ".+(ps|vs)3.+", name_shader ):
        defined_version = '30'
    else:
        defined_version = 'other'

    return defined_version

def get_all_shaders():

    result = []

    shader_list = {
        "shaders_count" : get_all_shaders_count(),
        "shaders" : {}
    }

    try: 
        for path in Path.cwd().rglob( '*.fxc' ):
            shader_dir = str( path.parent )
            shader_raw_name = str( path.name)
            shader_name = str( path.name ).split( '.' )[ 0 ]
            shader_version = defineShaderVersionByName( shader_name )


            if not shader_version in shader_list[ 'shaders' ]:
                shader_list[ 'shaders' ][ shader_version ] = {}
            shader_list[ 'shaders' ][ shader_version ][ shader_name ] = {
                    "raw_name" : shader_raw_name,
                    "raw_dir"  : shader_dir,
                    "dynamic"  : False,
                    "enabled"  : False
            }
        print( f'Shaders founded: { get_all_shaders_count() }' )
    except Exception as e:
        prWarn( 'Something went wrong when getting and generating shader list.' )
        exit(e)

    return shader_list

def shader_list_check():
    if not Path( SHADER_LIST_FILE ).exists():
        return False
    return True

def create_shader_list():

    if shader_list_check():
        return

    print( 'Creating shader list file' )

    try:
        json_data = dumps( get_all_shaders(), indent=4 )

        with open( SHADER_LIST_FILE, mode='w', encoding='utf-8' ) as shader_list_f:
            shader_list_f.write( json_data )
            shader_list_f.close()
        prSuccessful( f'Shader list file created { SHADER_LIST_FILE }' )
    except IOError as ioe:
        prWarn( f'Something went wrong while trying to write shader list file.\n' + ioe )
        exit( ioe )

def load_shader_list():
    shader_list_json = {}

    print('Loading shader list file')

    try:
        with open( SHADER_LIST_FILE, mode='r', encoding='utf-8' ) as shader_list_f:
            shader_list_json = load( shader_list_f )
            shader_list_f.close()
        prSuccessful( f'Shader list file loaded!\n' +
                f'Included { shader_list_json['shaders_count'] } shaders.')
    except IOError as ioe:
        prWarn( f'Something went wrong while trying to read shader list file.\n' + ioe )
        exit( ioe )

    return shader_list_json

def build_shader( dir_scr, dir_shaders, dir_mod, sh_compiler, threads_limit, dynamic_mode ):

    print( '\n' + '[ Compilation ]' )

    if not shader_list_check():
        prWarn( 'Shader list was not found! Creating...' )
        create_shader_list()
    else:
        prSuccessful( 'Shader list founded!' )
    
    shaders_list_raw = load_shader_list()

    shaders_list = shaders_list_raw[ 'shaders' ]

    #input('Edit configuration file and press ANY key...')

    for sh_versions in shaders_list:
        #supported_sh_version = [ "20b", "30", "40", "41", "50", "51" ]
        supported_sh_version = [ "20b", "30" ]
        version = None

        if sh_versions in supported_sh_version:
            version = sh_versions
        else:
            prBtw( "Found unsupported shader version! Skipping..." )
            return

        for shader in shaders_list[ sh_versions ]:
            if not shaders_list[ sh_versions ][ shader ][ "enabled" ]:
                continue
            print( f'Sended { version } version of the { shader } to a compiler' )

            sh_raw_dir = shaders_list[ sh_versions ][shader][ "raw_dir" ]
            sh_raw_name = shaders_list[ sh_versions ][shader][ "raw_name" ]
            sh_dynamic = True if dynamic_mode else shaders_list[ sh_versions ][shader][ "dynamic" ]
            sh_c_name = shader + ".vcs"

            worker_config = []

            worker_config.append( f'{ dir_scr + '/' + sh_compiler }' )
            worker_config.append( f'-threads { threads_limit }' )
            worker_config.append( f'-ver { version }' )
            if sh_dynamic:
                worker_config.append( '-dynamic' )
            worker_config.append( f'-shaderpath { sh_raw_dir } { sh_raw_name }' )

            #worker_config = f'& { dir_scr + '/' + sh_compiler } -threads 15 -ver { version } -shaderpath { sh_raw_dir } { sh_raw_name }'

            compiler_command = '& ' + ' '.join( worker_config)

            print(  f'\033[96mCMP:\033[00m { sh_compiler } ' +
                    f'| \033[96mThreads:\033[00m { threads_limit } ' +
                    f'| \033[96mDynamic mode:\033[00m { sh_dynamic } ' +
                    f'| \033[96mShader:\033[00m {sh_raw_name} \n' )

            #   Prepare state:
            #    Compiling 377,487,360 commands  in 15,728,640 static combos, setup took 0 seconds.
            #    r'^.+in(.*?)static'
            #   Compiling state:
            #    Compiling vertexlit_and_unlit_generic_ps30 [11,801,167 remaining] 12 seconds elapsed (490934 c/s, est. remaining 24 seconds)
            #    r'^\D+ (?P<shader_name>.*?) \[(?P<combos_remain>.*?)\D+\] (?P<elapsed_time>\d+).*\((?P<combos_per_sec>\d+) .* (?P<remain_time>\d+)'
            #    https://regex101.com/r/VSjd6U/1

            run( [ "powershell", compiler_command ] )

            src_shader_file = dir_shaders + "/shaders/fxc/" + sh_c_name
            game_shader_file = dir_mod + "/shaders/fxc/" + sh_c_name

            print(f"Copy shader { src_shader_file } to game dir { game_shader_file }")

            copyfile( src_shader_file, game_shader_file )


if __name__ == '__main__':
    os.system( 'cls' if os.name == 'nt' else 'clear' )

    configuraiton = cConf()

    build_shader( configuraiton.dir_src, configuraiton.dir_shaders,
                configuraiton.dir_mod, configuraiton.shader_compiler,
                configuraiton.threads, configuraiton.force_dynamic )