import os
import subprocess
import glob
import json
from PIL import Image
from pathlib import Path
import numpy as np
from skimage.metrics import structural_similarity as ssim
import cv2
from IPython.display import display, Image as IPyImage

class VideoProcessor:
    def __init__(self, video_path):
        """
        Initialize VideoProcessor with video metadata
        
        Args:
            video_path (str): Path to video file
        """
        # Check for FFmpeg installation
        self._check_ffmpeg()
        
        self.video_path = video_path
        self.output_dir = Path(video_path).parent / Path(video_path).stem
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Get video metadata
        self.metadata = self._get_video_info()
        
        print("Video Information:")
        print(f"Duration: {self.metadata['duration']} seconds")
        print(f"Resolution: {self.metadata['width']}x{self.metadata['height']}")
        print(f"FPS: {self.metadata['fps']}")
        print(f"Output directory: {self.output_dir}")

    def _check_ffmpeg(self):
        """Check if ffmpeg and ffprobe are installed"""
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
            subprocess.run(['ffprobe', '-version'], capture_output=True, check=True)
        except FileNotFoundError:
            raise RuntimeError(
                "FFmpeg is not installed. Please install FFmpeg:\n"
                "- Ubuntu/Debian: sudo apt-get install ffmpeg\n"
                "- MacOS: brew install ffmpeg\n"
                "- Windows: Download from https://ffmpeg.org/download.html"
            )

    def _get_video_info(self):
        """Get basic video metadata using ffprobe"""
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            self.video_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        data = json.loads(result.stdout)
        
        # Find video stream
        video_stream = next(s for s in data['streams'] if s['codec_type'] == 'video')
        
        # Calculate FPS
        fps_parts = video_stream['r_frame_rate'].split('/')
        fps = float(fps_parts[0]) / float(fps_parts[1])
        
        return {
            'duration': float(data['format']['duration']),
            'width': int(video_stream['width']),
            'height': int(video_stream['height']),
            'fps': fps,
            'total_frames': int(video_stream.get('nb_frames', 0))
        }

    def extract_frame_at_timestamp(self, timestamp_seconds, output_filename=None, display_frame=True):
        """
        Extract a single frame at a specific timestamp
        
        Args:
            timestamp_seconds (float): Timestamp in seconds
            output_filename (str, optional): Output filename. If None, auto-generated
            display_frame (bool): Whether to display the frame in the notebook
        
        Returns:
            str: Path to extracted frame
        """
        if output_filename is None:
            output_filename = f"frame_{timestamp_seconds:.3f}.jpg"
        
        output_path = self.output_dir / output_filename
        
        command = [
            'ffmpeg',
            '-ss', str(timestamp_seconds),
            '-i', str(self.video_path),
            '-frames:v', '1',
            '-q:v', '2',
            '-y',
            str(output_path)
        ]
        
        subprocess.run(command, check=True, capture_output=True)
        
        if display_frame:
            print(f"Frame at {timestamp_seconds} seconds:")
            with Image.open(output_path) as img:
                # Resize for display
                width = 800
                ratio = width / img.size[0]
                height = int(img.size[1] * ratio)
                resized_img = img.resize((width, height), Image.LANCZOS)
                display(IPyImage(data=resized_img._repr_png_()))
        
        return str(output_path)

    def extract_frames(self, fps=1, max_resolution=None):
        """
        Extract frames from entire video at specified FPS
        
        Args:
            fps (float): Frames per second to extract
            max_resolution (tuple, optional): (width, height) to resize frames
        
        Returns:
            list: Paths to extracted frames
        """
        frames_dir = self.output_dir / 'frames'
        os.makedirs(frames_dir, exist_ok=True)

        filters = [f"fps={fps}"]
        if max_resolution:
            filters.append(f"scale={max_resolution[0]}:{max_resolution[1]}")

        command = [
            'ffmpeg',
            '-i', str(self.video_path),
            '-vf', ','.join(filters),
            '-frame_pts', '1',
            '-vsync', '0',
            '-q:v', '2',
            f"{frames_dir}/frame_%07d.jpg"
        ]
        
        subprocess.run(command, check=True, capture_output=True)
        return sorted(glob.glob(f"{frames_dir}/*.jpg"))

    def compare_frames(self, image1_path, image2_path):
        """
        Compare two frames using structural similarity index
        
        Args:
            image1_path (str): Path to first image
            image2_path (str): Path to second image
            
        Returns:
            float: Similarity score between 0 and 1
        """
        # Read images
        img1 = cv2.imread(image1_path)
        img2 = cv2.imread(image2_path)
        
        # Convert to grayscale
        gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
        
        # Compute SSIM
        score = ssim(gray1, gray2)
        return score

    def filter_distinct_frames(self, frame_paths, similarity_threshold=0.85):
        """
        Filter frames to keep only distinct ones based on similarity threshold
        
        Args:
            frame_paths (list): List of paths to frames
            similarity_threshold (float): Threshold above which frames are considered too similar
                                       (0 to 1, where 1 is identical)
        
        Returns:
            list: Paths to distinct frames
        """
        if not frame_paths:
            return []

        distinct_frames = [frame_paths[0]]  # Always keep the first frame
        
        print("Analyzing frames for distinctiveness...")
        total_frames = len(frame_paths)
        
        for i in range(1, len(frame_paths)):
            # Progress update
            if i % 10 == 0:
                print(f"Processing frame {i}/{total_frames}...")
                
            # Compare with previous distinct frame
            similarity = self.compare_frames(distinct_frames[-1], frame_paths[i])
            
            # If frame is sufficiently different, keep it
            if similarity < similarity_threshold:
                distinct_frames.append(frame_paths[i])
        
        print(f"Retained {len(distinct_frames)} distinct frames out of {total_frames}")
        return distinct_frames

    def create_composite(self, image_paths, columns, border_width=2):
        """
        Create a composite grid image from multiple frames
        
        Args:
            image_paths (list): List of paths to images
            columns (int): Number of columns in grid
            border_width (int): Width of border between images
        
        Returns:
            PIL.Image: Composite image
        """
        if not image_paths:
            raise ValueError("No images provided")

        # Open first image to get dimensions
        with Image.open(image_paths[0]) as img:
            img_width, img_height = img.size

        # Calculate rows needed
        rows = (len(image_paths) + columns - 1) // columns

        # Create blank composite image
        composite_width = columns * img_width + (columns + 1) * border_width
        composite_height = rows * img_height + (rows + 1) * border_width
        composite = Image.new('RGB', (composite_width, composite_height), 'white')

        # Place images in grid
        for idx, img_path in enumerate(image_paths):
            row = idx // columns
            col = idx % columns
            
            with Image.open(img_path) as img:
                x = col * (img_width + border_width) + border_width
                y = row * (img_height + border_width) + border_width
                composite.paste(img, (x, y))

        return composite

    def create_composite_from_distinct_frames(self, frame_paths, columns, 
                                           similarity_threshold=0.85, 
                                           border_width=2):
        """
        Create a composite image from distinct frames
        
        Args:
            frame_paths (list): List of paths to frames
            columns (int): Number of columns in grid
            similarity_threshold (float): Threshold for frame similarity
            border_width (int): Width of border between images
            
        Returns:
            PIL.Image: Composite image of distinct frames
        """
        # First filter for distinct frames
        distinct_frames = self.filter_distinct_frames(frame_paths, similarity_threshold)
        
        # Then create composite from distinct frames
        return self.create_composite(distinct_frames, columns, border_width)
