import json
import os
import tempfile
from pathlib import Path

from flask import Flask, request, render_template_string, redirect, url_for, flash
from werkzeug.utils import secure_filename

# Import your existing functions from your project.
from generate_scenarios import generate_test_scenarios_for_all
from openapi_parser import load_api_spec, endpoints

# Configure Flask app
app = Flask(__name__)
app.secret_key = "supersecretkey"  # For flashing messages
UPLOAD_FOLDER = tempfile.gettempdir()
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'yaml', 'yml', 'json'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# HTML template for the upload form (using Bootstrap)
UPLOAD_FORM = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>API Test Scenario Generator</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
  <div class="container mt-4">
    <h1 class="mb-4">API Test Scenario Generator</h1>
    {% with messages = get_flashed_messages() %}
      {% if messages %}
        <div class="alert alert-danger">
          <ul class="mb-0">
            {% for message in messages %}
              <li>{{ message }}</li>
            {% endfor %}
          </ul>
        </div>
      {% endif %}
    {% endwith %}
    <form method="post" action="{{ url_for('upload_spec') }}" enctype="multipart/form-data">
      <div class="mb-3">
        <label for="specFile" class="form-label">Select API Spec File</label>
        <input type="file" class="form-control" id="specFile" name="spec_file">
      </div>
      <button type="submit" class="btn btn-primary">Generate Test Scenarios</button>
    </form>
  </div>
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

# HTML template for displaying the results
RESULT_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Generated Test Scenarios</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    pre {
      background-color: #f8f9fa;
      padding: 1rem;
      border: 1px solid #dee2e6;
      border-radius: .25rem;
    }
  </style>
</head>
<body>
  <div class="container mt-4">
    <h1 class="mb-4">Generated Test Scenarios</h1>
    <div class="card mb-4">
      <div class="card-body">
        <pre>{{ output }}</pre>
      </div>
    </div>
    <a href="{{ url_for('upload_spec') }}" class="btn btn-secondary">Upload another file</a>
  </div>
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def upload_spec():
    if request.method == "POST":
        # Check if the post request has the file part
        if 'spec_file' not in request.files:
            flash("No file part")
            return redirect(request.url)
        file = request.files['spec_file']
        if file.filename == "":
            flash("No selected file")
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            temp_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(temp_path)
            try:
                # Load and process the API spec.
                api_spec = load_api_spec(Path(temp_path))
                endpoints_list = endpoints(api_spec)
                scenarios = generate_test_scenarios_for_all(endpoints_list)
                output = json.dumps(scenarios, indent=4)
            except Exception as e:
                output = f"Error generating scenarios: {str(e)}"
            finally:
                # Optionally remove the temporary file.
                os.remove(temp_path)
            return render_template_string(RESULT_TEMPLATE, output=output)
        else:
            flash("Allowed file types are YAML and JSON.")
            return redirect(request.url)
    return render_template_string(UPLOAD_FORM)

if __name__ == "__main__":
    # Run the Flask development server.
    app.run(debug=True)
