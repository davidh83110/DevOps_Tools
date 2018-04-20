import os
from flask import Flask, request, url_for, send_from_directory
from werkzeug import secure_filename

ALLOWED_EXTENSIONS = set(['xls', 'xlsx', 'txt', 'rb', 'erb'])

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.getcwd()


html = '''
    <!DOCTYPE html>
    <title>Upload File to Remote Machine</title>
    <h1>UPLOAD</h1>
    <form method=post enctype=multipart/form-data>
         <input type=file name=file>
         <input type=submit value=upload>
    </form>
    '''


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    
    command = 'scp {} david@10.10.10.10:/tmp'.format(app.config['UPLOAD_FOLDER']+'/'+filename)
    print(command)
    
    scp_file = os.popen(command)
    
    return (send_from_directory(app.config['UPLOAD_FOLDER'],
                               filename))


@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            file_url = url_for('uploaded_file', filename=filename)
            return html + '<br><src=' + file_url + '>'
    return html


if __name__ == '__main__':
    app.run(host='0.0.0.0', port='8080')
