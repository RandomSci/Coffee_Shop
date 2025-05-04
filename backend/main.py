from flask import Flask, render_template, send_from_directory
import os
from connections.routes import routes

project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

static_folder = os.path.join(project_dir, 'frontend', 'static')

app = Flask(__name__,
    template_folder=os.path.join(project_dir, 'frontend', 'templates'),
    static_url_path='/static',
    static_folder=static_folder)

app.config['SECRET_KEY'] = 'anything'
app.config['DEBUG'] = True

app.register_blueprint(routes)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500

if __name__ == '__main__':
    if os.path.exists(static_folder):
        for root, dirs, files in os.walk(static_folder):
            rel_path = os.path.relpath(root, static_folder)
                
        images_dir = os.path.join(static_folder, 'images')
    app.run(host='0.0.0.0', port=5000)