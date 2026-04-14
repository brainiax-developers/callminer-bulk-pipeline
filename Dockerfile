FROM public.ecr.aws/lambda/python:3.12

ENV PYTHONPATH="${LAMBDA_TASK_ROOT}/src"

# Only ship scheduler source in the runtime image.
COPY src/ "${LAMBDA_TASK_ROOT}/src/"

CMD ["callminer_bulk_pipeline.handlers.bulkapi_scheduler.lambda_handler"]
