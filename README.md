# 🌐 ShadowMap | Public Documentation Site

This branch (`gh-pages`) contains the source code for the **ShadowMap Technical Case Study** website. 

### 🔗 Live Access
The contents of this branch are automatically deployed to:
**[https://medhansh5.github.io/ShadowMap/](https://medhansh5.github.io/ShadowMap/)**

---

## 🛠 Branch Purpose
Unlike the `main` branch, which houses the Python backend, PostgreSQL schemas, and ML models, this branch is an **independent orphan branch** dedicated to:
* **Technical Documentation:** Bridging the gap between the hardware integration on "The Baron" (Classic 350) and the software stack.
* **Public Visualization:** Serving the landing page and case study for the project to non-technical stakeholders and university admissions.
* **Asset Hosting:** Storing hardware schematics, confusion matrices, and telemetry visualization exports.

## 🚀 Deployment Workflow
1.  Changes are made locally in Termux.
2.  Commits are pushed to `origin gh-pages`.
3.  GitHub Actions triggers a build to update the live site.

## 📁 Directory Structure
* `index.html`: The core technical case study (Tailwind CSS).
* `assets/`: (Planned) High-res images of the sensor rig and data plots.

---
*Developed by Medhansh Kabadwal as part of the ShadowMap Project (2026).*
