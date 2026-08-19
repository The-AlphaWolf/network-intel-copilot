FROM python:3.12-slim
RUN pip install --no-cache-dir mlflow==3.15.1
EXPOSE 5000
CMD ["mlflow", "server", \
     "--backend-store-uri", "sqlite:///mlflow-data/mlflow.db", \
     "--default-artifact-root", "/mlflow-data/artifacts", \
     "--host", "0.0.0.0", "--port", "5000"]
