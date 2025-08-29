# ComicAI Studio: AWS Summit Seoul 2025

This repository contains sample applications showcased at the AWS Summit Seoul 2025, demonstrating the collaboration between AI and renowned Korean cartoonist Young-man Huh (허영만). The ComicAI Studio project represents a new paradigm where generative AI and human creators coexist and collaborate in the comic industry.

## Project Vision

Recent rapid advancements in AI technology have brought both new possibilities and concerns to the creative field. In the comic industry, there has been active debate about the introduction of AI. Some artists express concerns that AI might encroach on the unique domain of creators. However, we believe that these technological advancements can be opportunities rather than threats.

Our goal is to build a new comic ecosystem where generative AI and human creators can coexist and thrive together. Through this, artists can showcase more diverse works, and readers can enjoy richer content. This is not simply about adopting technology, but about presenting a new paradigm for the sustainable development of the comic industry.

## Applications

### FaceStory

FaceStory transforms visitors' faces into Young-man Huh's distinctive "Tazza" comic style and reconstructs facial coloring using Amazon Bedrock's image generation model, Nova Canvas, referencing the color palette from his "Beat" comic covers. This personalized experience also provides face reading interpretations inspired by Huh's physiognomy comic "Kkol," powered by Amazon Bedrock.

**Features:**
- Face transformation to comic style using Amazon Nova Canvas
- Color application based on "Beat" comic style
- Face reading/fortune telling based on facial features
- Available in both English and Korean

**Notebooks:**
- [01_face_to_comic_style.ipynb](facestory/01_face_to_comic_style.ipynb): Transform realistic face images into comic-style artwork
- [02_face_to_fortune.ipynb](facestory/02_face_to_fortune.ipynb): English version of face analysis and fortune reading
- [02_face_to_fortune_kr.ipynb](facestory/02_face_to_fortune_kr.ipynb): Korean version of face analysis and fortune reading

> **Note**: The Face Analysis and Fortune Reading notebooks (02_face_to_fortune.ipynb and 02_face_to_fortune_kr.ipynb) are part of the FaceStory corner, inspired by Huh's physiognomy comic "Kkol."

### ToonMirror

ToonMirror is an interactive mirror that uses Amazon SageMaker-based AI technology to recognize visitors' gestures and expressions in real-time, making characters from Young-man Huh's comics like "Sikgaek" mimic the same actions. It converts visitors' unique facial features into a comic style and reflects their movements in real-time, offering a special experience as if they've entered Huh's works.

### ToonCraft

ToonCraft generates dynamic questionnaires using Amazon Bedrock's text generation model, Nova Lite, based on episodes chosen by visitors, and recommends food from Young-man Huh's "Baekban Gihaeng" according to their answers. The cooking process of the recommended food is transformed into a 4-panel comic through Amazon Bedrock's image generation model, Nova Canvas, and video generation model, Nova Reel, creating a user-participatory service.

**Features:**
- Text-guided image regeneration from food images
- Spatial and temporal expansion of images via outpainting and video synthesis
- Semantic-driven character generation from facial images
- Virtual try-on functionality for placing food items onto empty plates with multiple merge styles

**Notebooks:**
- [01_image_regeneration.ipynb](tooncraft/01_image_regeneration.ipynb): Generate new food images by extracting prompts from a single image and using text-to-image and image-to-image techniques
- [02_image_to_video_expansion.ipynb](tooncraft/02_image_to_video_expansion.ipynb): Expand the visible region of an image using outpainting, then generate a smooth video using Nova Reel
- [03_face_to_persona_generation.ipynb](tooncraft/03_face_to_persona_generation.ipynb): Extract personality traits from a face and generate AI character portraits based on inferred persona
- [04_virtual_try_on_food_theme.ipynb](tooncraft/04_virtual_try_on_food_theme.ipynb): Virtual try-on functionality that places food items onto empty plates using Amazon Nova Canvas with multiple merge styles (SEAMLESS, BALANCED, DETAILED)

> **Note**: The Comic Style Transformation functionality is part of the ToonCraft corner, which transforms cooking processes into comic-style artwork.



## Technical Stack

- **Amazon Bedrock**: Foundation for generative AI capabilities
  - **Nova Canvas**: Image generation model for comic style transformation and food visualization
  - **Nova Lite**: Text generation model for dynamic questionnaires and face reading
  - **Nova Reel**: Video generation model for animated cooking processes
- **Amazon SageMaker**: Powers real-time gesture recognition

## Sample Applications Organization

This repository is organized by feature rather than by exhibition corner:

1. **facestory/**: Contains notebooks for both FaceStory features:
   - Comic style transformation (01_face_to_comic_style.ipynb)
   - Face analysis and fortune reading (02_face_to_fortune.ipynb and 02_face_to_fortune_kr.ipynb)

2. **tooncraft/**: Contains notebooks for visual content regeneration:
   - Food image regeneration (01_image_regeneration.ipynb)
   - Image-to-video expansion (02_image_to_video_expansion.ipynb)
   - Face-to-persona character generation (03_face_to_persona_generation.ipynb)
   - Virtual try-on for food placement (04_virtual_try_on_food_theme.ipynb)

## Code Implementation

The code provided in this repository has been simplified to focus on the core functionality and key concepts:

- Sample implementations demonstrate the essential techniques without complex production-level code
- Examples use placeholder images and generic assets instead of copyrighted materials
- Workflows have been streamlined to make the concepts more accessible to developers
- Each notebook includes detailed comments to explain the approach and methodology

## Getting Started

Each application folder contains detailed instructions on how to run the demos:

1. [FaceStory](facestory/): Transform faces into comic style and generate fortune readings
2. ToonMirror: *(Coming soon)* Interactive real-time comic character mirroring
3. [ToonCraft](tooncraft/): Visual content regeneration with AI models


## Requirements

- Access to Amazon Bedrock (Nova Canvas, Nova Lite, and Nova Reel models)
- Amazon SageMaker environment
- Python 3.8+
- Required Python packages (specified in each application's documentation)

## Acknowledgements

This project is a collaboration between AWS and Young-man Huh, one of Korea's most renowned cartoonists. We extend our gratitude to Young-man Huh for his artistic contributions and vision in exploring the intersection of traditional comic art and cutting-edge AI technology.

## Copyright Notice

All comic works referenced in this project (including "Tazza", "Beat", "Kkol", "Sikgaek", and "Baekban Gihaeng") are copyrighted materials owned by Young-man Huh. The sample applications in this repository use generic images and placeholders instead of actual comic artwork to respect these copyrights. Any implementation using the actual comic artwork would require proper licensing and permissions from the copyright holder.

---

*ComicAI Studio was showcased at AWS Summit Seoul 2025, demonstrating the harmonious fusion of comic art and AI technology while respecting the creator's originality and providing visitors with a deeper experience of the works.*