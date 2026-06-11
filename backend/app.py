from flask import Flask

from backend.config import DEBUG, FRONTEND_DIR, HOST, PORT
from backend.routes import bank, health, index, nfs, operations, parsed, rebuild, search, specs, stories, topology, yaml


def create_app() -> Flask:
    app = Flask(__name__, static_folder=str(FRONTEND_DIR), static_url_path="/static")

    app.register_blueprint(index.bp)
    app.register_blueprint(yaml.bp)
    app.register_blueprint(parsed.bp)
    app.register_blueprint(bank.bp)
    app.register_blueprint(search.bp)
    app.register_blueprint(rebuild.bp)
    app.register_blueprint(health.bp)
    app.register_blueprint(topology.bp)
    app.register_blueprint(specs.bp)
    app.register_blueprint(operations.bp)
    app.register_blueprint(stories.bp)
    app.register_blueprint(nfs.bp)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host=HOST, port=PORT, debug=DEBUG)
