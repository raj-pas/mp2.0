from __future__ import annotations

import time

from django.core.management.base import BaseCommand

from web.api.review_processing import claim_next_job, process_job, record_worker_heartbeat


class Command(BaseCommand):
    help = "Process MP2.0 review ingestion jobs from the Postgres-backed queue."

    def add_arguments(self, parser):  # noqa: ANN001
        parser.add_argument("--once", action="store_true", help="Process available jobs once.")
        parser.add_argument("--sleep", type=float, default=2.0, help="Idle sleep in seconds.")

    def handle(self, *args, **options):  # noqa: ANN002, ANN003
        once = options["once"]
        sleep_seconds = options["sleep"]
        record_worker_heartbeat(metadata={"stage": "starting"})

        while True:
            job = claim_next_job()
            if job is None:
                record_worker_heartbeat(metadata={"stage": "idle"})
                if once:
                    self.stdout.write("No queued review jobs.")
                    return
                time.sleep(sleep_seconds)
                continue

            self.stdout.write(f"Processing review job {job.id} ({job.job_type})")
            process_job(job)
            if once:
                return
