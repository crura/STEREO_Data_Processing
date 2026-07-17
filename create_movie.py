from moviepy.editor import ImageClip, concatenate_videoclips

from pathlib import Path

# Define the directory path
dir_path = Path('/Users/crura/Desktop/Research/2026_Summer_Project/Representative_Images/B/4_per_day/Monthly_Gifs/B/median')

# Fetch, filter out folders, and sort alphabetically
files = sorted([p for p in dir_path.iterdir() if p.is_file()])

# 1. Load your GIF files as ImageClips
clip1 = ImageClip("first.gif")
clip2 = ImageClip("second.gif")

# 2. Concatenate the clips into a sequence
final_video = concatenate_videoclips(files)

# 3. Export the result as an MP4 movie
# Note: Adjust the fps (frames per second) based on your GIFs
final_video.write_videofile("/Users/crura/Desktop/Research/2026_Summer_Project/Representative_Images/B/4_per_day/Monthly_Gifs/B/median_year.mp4", fps=24, codec="libx264")
