FROM public.ecr.aws/lambda/python:3.12

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies to /opt/python to avoid overwriting Lambda runtime packages
RUN uv export --no-dev --no-hashes -o requirements.txt && \
    uv pip install --no-cache -r requirements.txt --target /opt/python --index-url https://pypi.org/simple/

ENV PYTHONPATH=/opt/python

# Copy handler code directly into task root
COPY ./src ${LAMBDA_TASK_ROOT}

CMD ["pyiceberg_make_table.lambda_handler"]
