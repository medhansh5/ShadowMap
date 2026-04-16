# HTML Templates
This directory contains the Jinja2 templates for the ShadowMap web interface.

### Files
* **index.html**: The main entry point. It initializes the Leaflet.js map container and loads the necessary CSS/JS assets.

### Integration
Flask looks for this folder by default to serve pages via the `render_template()` function.
