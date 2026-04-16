# Static Assets
This directory houses the frontend logic and styling that is served directly to the client's browser.

### Structure
* **/js/map.js**: Contains the Leaflet.js logic. It fetches road quality data from the `/roads` API endpoint and renders color-coded circles based on the quality score.
* **/css/style.css**: (Optional) Custom styling for the map UI and dashboard overlays.

### Note
When referencing these files in templates, use the Flask `url_for('static', filename='...')` helper to ensure correct path routing.
