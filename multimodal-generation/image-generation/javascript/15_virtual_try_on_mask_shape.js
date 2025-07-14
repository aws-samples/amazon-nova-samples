import { BedrockImageGenerator } from './BedrockImageGenerator.js';
import { imageToBase64 } from './fileUtils.js';

// Path to image to be edited
const sourceImagePath = "../images/vto-images/vto_mask_shape_source.jpg";
const referenceImagePath = "../images/vto-images/vto_mask_shape_reference.jpg";


const generateImages = async () => {

    // Format timestamp for unique directory naming
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
    const outputDirectory = `output/${timestamp}`;

    const generator = new BedrockImageGenerator({ outputDirectory });


    try {
            // Read the images from file and encode them as base64 strings
            const sourceImageBase64 = await imageToBase64(sourceImagePath);
            const referenceImageBase64 = await imageToBase64(referenceImagePath);

            const params = {
                taskType: "VIRTUAL_TRY_ON",
                virtualTryOnParams: {
                    sourceImage: sourceImageBase64,
                    referenceImage: referenceImageBase64,
                    maskType: "GARMENT",
                    garmentBasedMask: {
                        garmentClass: "FULL_BODY",
                        maskShape: "BOUNDING_BOX"
                    }
                },
                imageGenerationConfig: {
                    numberOfImages: 1,
                    quality: "standard",
                    cfgScale: 6.5,
                    seed: Math.floor(Math.random() * 2147483646)
                }
            };
            
       const images = await generator.generateImages(params);
            console.log('Generated images:', images.join(', '));
        } catch (err) {
            console.error('Image generation failed:', err.message);
            process.exit(1);
        }
    };

// Self-executing async function
(async () => {
    try {
        await generateImages();
    } catch (err) {
        console.error('Fatal error:', err.message);
        process.exit(1);
    }
})();
