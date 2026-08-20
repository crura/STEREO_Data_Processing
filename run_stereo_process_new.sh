source ~/miniconda3/etc/profile.d/conda.sh &&
conda init bash &&
conda activate test_env &&
python3 -m venv env &&
source env/bin/activate &&
pip install -r requirements.txt &&
git_repo=$(git rev-parse --show-toplevel) &&
sswPath='~/SSW' &&
# export SSW /Users/crura/SSW
# source $SSW/gen/setup/setup.ssw \loud

# User sets these paths
export IDL_DIR="/Applications/harris/idl89" &&
export secchi="/Volumes/Seagate/Chris/sswdb/secchi" &&
export SECCHI_BKG="/Volumes/Seagate/Chris/sswdb/secchi/backgrounds" &&
export SSWDB="/Volumes/Seagate/Chris/sswdb" &&
export sdb="/Volumes/Seagate/Chris/sswdb" &&
export VSO_SERVER="http://netdrms02.nispdc.nso.edu/cgi/vsoi_tabdelim" &&

(echo "ssw_path" &&
echo ".compile -v '$sswPath/gen/idl/string/strjustify.pro'" &&
echo ".compile -v '$sswPath/gen/idl/system/strrep_logenv.pro'" &&
echo ".compile -v '$sswPath/gen/idl/string/prstr.pro'" &&
echo ".compile -v '$sswPath/gen/idl/genutil/uniqo.pro'" &&
echo ".compile -v '$git_repo/IDL_Utilites/concat_dir.pro'" &&
echo "ssw_path, '$sswPath/gen'" &&
echo "ssw_path, '$sswPath/hinode'" &&
echo "ssw_path, '$sswPath/offline'" &&
echo "ssw_path, '$sswPath/proba2'" &&
echo "ssw_path, '$sswPath/sdo'" &&
echo "ssw_path, '$sswPath/site'" &&
echo "ssw_path, '$sswPath/so'" &&
echo "ssw_path, '$sswPath/soho'" &&
echo "ssw_path, '$sswPath/stereo'" &&
echo "ssw_path, '$sswPath/trace'" &&
echo "ssw_path, '$sswPath/vobs'" &&
echo "ssw_path, '$sswPath/packages'" &&
# echo ".compile -v '/Users/crura/Desktop/Research/idlroutines/download.pro'" &&
echo ".compile -v '$sswPath/packages/forward/idl/DEFAULTS/for_settingdefaults.pro'" &&
echo ".compile -v '$sswPath/gen/idl/util/default.pro'" &&
echo ".compile -v '$git_repo/IDL_Utilites/linspace.pro'" &&
echo ".compile -v '$git_repo/stereo_process.pro'" &&

# from https://gist.github.com/pkuczynski/8665367
parse_yaml() {
    local prefix=$2
    local s='[[:space:]]*' w='[a-zA-Z0-9_]*' fs=$(echo @|tr @ '\034')
    sed -ne "s|^\($s\)\($w\)$s:$s\"\(.*\)\"$s\$|\1$fs\2$fs\3|p" \
        -e "s|^\($s\)\($w\)$s:$s\(.*\)$s\$|\1$fs\2$fs\3|p"  $1 |
    awk -F$fs '{
        indent = length($1)/2;
        vname[indent] = $2;
        for (i in vname) {if (i > indent) {delete vname[i]}}
        if (length($3) > 0) {
        vn=""; for (i=0; i<indent; i++) {vn=(vn)(vname[i])("_")}
        printf("%s%s%s=\"%s\"\n", "'$prefix'",vn, $2, $3);
        }
    }'
}

eval $(parse_yaml config.yaml "config_")
echo $config_input_path

# Specify the parent directory to loop through its subdirectories
parent_directory="$config_input_path/A" &&

# Loop through subdirectories
for dir in "$parent_directory"/*/; do
    # Call the custom function for each subdirectory
    echo "stereo_process('$dir')"
done

# Specify the parent directory to loop through its subdirectories
parent_directory="$config_input_path/B" &&

# Loop through subdirectories
for dir in "$parent_directory"/*/; do
    # Call the custom function for each subdirectory
    echo "stereo_process('$dir')"
done
cat) |
/Users/crura/Documents/bin/ssw
deactivate
