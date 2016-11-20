motion_cfg=$1
storage_dir=$2

# "daemon off"
sed -i -E "s/^(daemon)\s+on(.*)?/\1 off/g" $motion_cfg
# "resolution width"
sed -i -E "s/^(width)\s+[0-9]+(.*)?/\1 640/g" $motion_cfg
# "resolution height"
sed -i -E "s/^(height)\s+[0-9]+(.*)?/\1 480/g" $motion_cfg
# "framerate/stream framerate"
sed -i -E "s/^(framerate)\s+[0-9]+(.*)?/\1 15/g" $motion_cfg
sed -i -E "s/^(stream_maxrate)\s+[0-9]+(.*)?/\1 15/g" $motion_cfg
# "pre-capture seconds"
sed -i -E "s/^(pre_capture)\s+[0-9]+(.*)?/\1 5/g" $motion_cfg
# "post-capture seconds"
sed -i -E "s/^(post_capture)\s+[0-9]+(.*)?/\1 5/g" $motion_cfg
# "motion storage directory"
sed -i -E "s@^(target_dir)\s+(.*)?@\1 $storage_dir@g" $motion_cfg
# "motion log"
sed -i -E "s@^(#)?\s+?logfile\s+.*@#logfile@g" $motion_cfg
# "output picture type"
sed -i -E "s/^(output_pictures)\s+(.*)?/\1 best/g" $motion_cfg
# "snapshot filename"
sed -i -E "s/^(snapshot_filename)\s+(.*)?/\1 %Y%m%d%H%M%S-snapshot/g" $motion_cfg
# "picture filename"
sed -i -E "s/^(picture_filename)\s+(.*)?/\1 %Y%m%d%H%M%S-%q/g" $motion_cfg
# "movie filename"
sed -i -E "s/^(movie_filename)\s+(.*)?/\1 %Y%m%d%H%M%S/g" $motion_cfg
# "script for when events start"
sed -i -E "s/^(;)?(\s+)?(on_event_start)\s+(.*)?/\3 things2c notify Motion; things2c publish --topic motion_event_start/g" $motion_cfg
# "script for when events end"
sed -i -E "s/^(;)?(\s+)?(on_event_end)\s+(.*)?/\3 things2c publish --topic motion_event_end/g" $motion_cfg
# "script for when motion is detected"
sed -i -E "s/^(;)?(\s+)?(on_motion_detected)\s+(.*)?/\3 things2c publish --topic motion_detected/g" $motion_cfg
# "script for when movie has ended"
sed -i -E "s/^(;)?(\s+)?(on_movie_end)\s+(.*)?/\3 things2c publish --topic motion_filesync_queue --payload=%f/g" $motion_cfg
# "script for when picture has been saved"
sed -i -E "s/^(;)?(\s+)?(on_picture_save)\s+(.*)?/\3 things2c publish --topic motion_filesync_queue --payload=%f/g" $motion_cfg
# "don't restrict streaming to localhost"
sed -i -E "s/^(stream_localhost)\s+on(.*)?/\1 off/g" $motion_cfg
