from flask import Flask, url_for, render_template, request, redirect, make_response, send_from_directory, abort
from werkzeug.utils import secure_filename
from pathlib import Path
import pandas as pd
import geocoder
import requests
import os

app = Flask('__name__')
if app.config['ENV'] == 'Production':
    app.config.from_object('config.ProductionConfig')
else:
    app.config.from_object('config.DevelopmentConfig')
print(f'ENV is set to: {app.config["ENV"]}')

@app.route('/')
def index():
    return render_template('index.html')

def allowed_file(filename):
    # We only want files with a . in the filename
    if not '.' in filename:
        return False
    # Split the extension from the filename
    ext = filename.rsplit('.', 1)[1]
    # Check if the extension is in ALLOWED_FILE_EXTENSIONS
    if ext.upper() in app.config['ALLOWED_FILE_EXTENSIONS']:
        return True
    else:
        return False
 
@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    global filename

    if request.method == 'POST':
        if request.files:
            file = request.files['name']

            if file.filename == '':
                print('No filename')
                return redirect(request.url)

            if allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['FILE_UPLOADS'], filename))
                print("File saved")
                # print("Please upload your CSV file. The values containing address should be in a column named address or Address")
                server_file=f'static/uploads/{filename}'
                try:
                    if Path(f'{server_file}').suffix == '.csv':
                        df=pd.read_csv(f"{server_file}")

                        coordinates ={
                            'latitude':[],
                            'longitude':[],
                        }

                        if 'Address' in df.columns or 'address' in df.columns:
                            try:
                                for address in df['address']:
                                    # print(address)
                                    with requests.Session() as session:
                                        location=geocoder.arcgis(f'{address}', session=session)
                                        # print(location.latlng)
                                        coordinates['latitude'].append(location.lat)
                                        coordinates['longitude'].append(location.lng)

                            except KeyError:
                                for address in df['Address']:
                                    # print(address)
                                    with requests.Session() as session:
                                        location=geocoder.arcgis(f'{address}', session=session)
                                        # print(location.latlng)
                                        coordinates['latitude'].append(location.lat)
                                        coordinates['longitude'].append(location.lng)
                                
                            df['latitude']=coordinates['latitude']
                            df['langitude']=coordinates['longitude']
                            html_table = df.to_html()
                            message='Click DOWNLOAD to get updated file.'
                            btn = '<button type="button">Download</button>'
                            # print(df)
                            df.to_csv(f'static/client/{filename.rsplit(".", 1)[0]}_updated.csv', index=False)
                            resp = make_response(render_template('index.html', html_table=html_table, message=message, btn=btn))

                        else:
                            message='Please make sure you have an address column in your CSV file'
                            print(message)
                            resp = make_response(render_template('index.html', message=message))
                            
                except FileNotFoundError:
                    print('File not uploaded')
                    resp = make_response(render_template('index.html'))

            else:
                message="That file extension is not allowed!  FILE NOT CSV!!!"
                print('File not uploaded')
                print(message)
                resp = make_response(render_template('index.html', message=message))

    else:
        message='No file Chosen for upload'
        resp = make_response(render_template('index.html', message=message))
    return resp
   
@app.route('/download')
def download():
    try:
        return send_from_directory(app.config['CLIENT_FILES'], filename=f'{filename}.rsplit(".", 1)[0]_updated.csv', as_attachment=True)
    except FileNotFoundError:
        abort(404)

if __name__ == "__main__":
    app.run()
