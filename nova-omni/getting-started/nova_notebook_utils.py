import json

from IPython.display import Image, Markdown, display

import nova_utils


def _render_text_content(text_node, as_markdown=True):
    text = text_node["text"]
    if len(text) == 0:
        text = f"WARNING: Found unexpected empty text content:\n{json.dumps(text_node, indent=2)}\n\n"

    if as_markdown:
        display(Markdown(text))
    else:
        print(text)


def _render_reasoning_content(reasoning_node):
    reasoning_text = reasoning_node["reasoningContent"]["reasoningText"]["text"]
    print(reasoning_text)


def _render_image_content(image_node):
    image_bytes = image_node["image"]["source"]["bytes"]
    display(Image(data=image_bytes))


def render_content(content_list):
    for node_index, node in enumerate(content_list):
        if "text" in node:
            _render_text_content(node)
        elif "image" in node:
            _render_image_content(node)
        elif "reasoningContent" in node:
            _render_reasoning_content(node)
        else:
            raise ValueError(f"Unknown node type: {node}")


def render_response(response):
    request_id = nova_utils.extract_response_request_id(response)
    print(f"Request ID: {request_id}")

    content_list = response["output"]["message"]["content"]
    render_content(content_list)
