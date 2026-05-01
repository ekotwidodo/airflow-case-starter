from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

router = APIRouter()

records_processed = {"scraping": 0, "staging": 0, "mart": 0}
error_counts = {"scraping": 0, "staging": 0, "mart": 0}

def increment_records(job: str, count: int = 1):
    records_processed[job] += count

def increment_errors(job: str):
    error_counts[job] += 1

@router.get("/metrics", response_class=PlainTextResponse)
def metrics():
    lines = []
    for job, count in records_processed.items():
        lines.append(f'records_processed_total{{job="{job}"}} {count}')
    for job, count in error_counts.items():
        lines.append(f'error_count_total{{job="{job}"}} {count}')
    return "\n".join(lines)
