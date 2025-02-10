import json
import os
import tempfile
from pathlib import Path

from flask import Flask, request, render_template_string, redirect, url_for, flash
from werkzeug.utils import secure_filename

# Import your project functions (adjust the import paths as needed)
from generate_scenarios import generate_test_scenarios_for_all
from openapi_parser import load_api_spec, endpoints

# Configure Flask app
app = Flask(__name__)
app.secret_key = "supersecretkey"
UPLOAD_FOLDER = tempfile.gettempdir()
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {"yaml", "yml", "json"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# Landing page template with sky blue background and colorful design.
LANDING_PAGE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>API Test Scenario Generator</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    body {
      background-color: #87CEEB; /* Sky blue */
      color: #333;
    }
    .header-text {
      font-size: 2.5rem;
      font-weight: bold;
      color: #ffffff;
      text-shadow: 1px 1px 2px #000;
    }
    .lead {
      color: #f8f9fa;
    }
    .upload-card {
      margin-top: 50px;
      padding: 30px;
      border-radius: 10px;
      box-shadow: 0 4px 10px rgba(0,0,0,0.2);
      background-color: #ffffff;
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="text-center mt-5">
      <h1 class="header-text">API Test Scenario Generator</h1>
      <p class="lead">Upload your OpenAPI specification file to generate detailed test scenarios.</p>
    </div>
    {% with messages = get_flashed_messages() %}
      {% if messages %}
        <div class="alert alert-danger mt-4">
          <ul class="mb-0">
            {% for message in messages %}
              <li>{{ message }}</li>
            {% endfor %}
          </ul>
        </div>
      {% endif %}
    {% endwith %}
    <div class="card upload-card mx-auto" style="max-width: 600px;">
      <form method="post" action="{{ url_for('upload_spec') }}" enctype="multipart/form-data">
        <div class="mb-3">
          <label for="specFile" class="form-label">Select API Spec File</label>
          <input type="file" class="form-control" id="specFile" name="spec_file">
        </div>
        <button type="submit" class="btn btn-primary w-100">Generate Test Scenarios</button>
      </form>
    </div>
  </div>
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

# Result page template that groups output by endpoint.
RESULT_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Generated Test Scenarios</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    body {
      background-color: #f0f2f5;
    }
    .scenario-card {
      margin-bottom: 20px;
    }
    .card-header {
      background-color: #007bff;
      color: #fff;
    }
    .method-section {
      margin-bottom: 15px;
      padding: 10px;
      border: 1px solid #dee2e6;
      border-radius: 5px;
      background-color: #ffffff;
    }
  </style>
</head>
<body>
  <div class="container mt-4">
    <h1 class="mb-4">Generated Test Scenarios</h1>
    {% for endpoint, methods in grouped_endpoints.items() %}
      <div class="card scenario-card">
        <div class="card-header">
          <h4>Endpoint: {{ endpoint }}</h4>
        </div>
        <div class="card-body">
          {% for method, scenario in methods.items() %}
            <div class="method-section">
              <h5>Method: {{ method }}</h5>
              <p><strong>Scenario:</strong> {{ scenario.test_scenario }}</p>
              <p><strong>TestCase:</strong></p>
              <ul class="list-group">
                {% for step in scenario.test_steps %}
                  <li class="list-group-item">{{ step }}</li>
                {% endfor %}
              </ul>
            </div>
          {% endfor %}
        </div>
      </div>
    {% endfor %}
    <div class="text-center mt-4">
      <a href="{{ url_for('upload_spec') }}" class="btn btn-secondary">Upload another file</a>
    </div>
  </div>
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def upload_spec():
    if request.method == "POST":
        # Validate file presence and extension.
        if "spec_file" not in request.files:
            flash("No file part")
            return redirect(request.url)
        file = request.files["spec_file"]
        if file.filename == "":
            flash("No file selected")
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            temp_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(temp_path)
            try:
                # Process the API specification.
                api_spec = load_api_spec(Path(temp_path))
                endpoints_list = endpoints(api_spec)
                scenarios = generate_test_scenarios_for_all(endpoints_list)
                # Group scenarios by endpoint (path).
                grouped_endpoints = {}
                for key, scenario in scenarios.items():
                    # Expect key format: "METHOD path"
                    if " " in key:
                        method, path = key.split(" ", 1)
                    else:
                        method, path = "Other", key
                    if path not in grouped_endpoints:
                        grouped_endpoints[path] = {}
                    grouped_endpoints[path][method] = scenario
            except Exception as e:
                grouped_endpoints = {"Error": {"error": {"test_scenario": f"Error generating scenarios: {str(e)}", "test_steps": []}}}
            finally:
                os.remove(temp_path)
            return render_template_string(RESULT_TEMPLATE, grouped_endpoints=grouped_endpoints)
        else:
            flash("Allowed file types are YAML and JSON.")
            return redirect(request.url)
    return render_template_string(LANDING_PAGE)

if __name__ == "__main__":
    app.run(debug=True)
