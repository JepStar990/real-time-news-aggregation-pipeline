#!/usr/bin/env python3
import os
import signal
import logging
import time
import sys
import atexit
from concurrent.futures import ThreadPoolExecutor
import uvicorn
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from rss_feeder.scheduler import FeedScheduler
from rss_feeder.health import app as health_app  # Import the health app

# Create FastAPI application instance
app = FastAPI(title="RSS Feed Aggregator")

# Add Prometheus instrumentation
instrumentator = Instrumentator(
    should_group_status_codes=False,
    should_ignore_untemplated=True,
    should_respect_env_var=True
)
instrumentator.instrument(app).expose(app)

class ProcessManager:
    """Handles process cleanup and force termination"""
    def __init__(self):
        self._child_pids = set()
        self._shutdown_flag = False
        atexit.register(self.cleanup)

    def register_pid(self, pid):
        self._child_pids.add(pid)

    def cleanup(self):
        if self._shutdown_flag:
            return

        self._shutdown_flag = True
        logging.info("Cleaning up child processes...")

        for pid in self._child_pids.copy():
            try:
                os.kill(pid, signal.SIGTERM)
                time.sleep(0.5)
                if self._check_pid(pid):
                    os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            except Exception as e:
                logging.error(f"Error killing PID {pid}: {str(e)}")

    def _check_pid(self, pid):
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

class Application:
    def __init__(self):
        self.scheduler = None
        self.executor = None
        self.process_manager = ProcessManager()
        self._init_logging()
        self.logger = logging.getLogger('main')
        self.start_time = time.time()

    def _init_logging(self):
        """Configure application logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('rss_feeder.log')
            ]
        )

    @app.get("/")
    def read_root():
        return {"status": "running", "uptime": time.time() - self.start_time}

    # Mount health app
    app.mount("/health_api", health_app)  # Ensure proper mounting

    @app.get("/routes")
    def get_routes(self):
        """List all available routes"""
        return [{"path": route.path, "methods": route.methods} for route in app.routes]

    def run(self):
        """Main application entry point"""
        try:
            # Start services
            self.executor = ThreadPoolExecutor(max_workers=3)
            self.scheduler = FeedScheduler()

            # Register signal handlers
            signal.signal(signal.SIGINT, self._shutdown)
            signal.signal(signal.SIGTERM, self._shutdown)

            # Start components
            self.executor.submit(self._run_uvicorn)
            self.scheduler.start()

            self.logger.info("Application started (PID: %d)", os.getpid())
            self._monitor_activity()

        except Exception as e:
            self.logger.error("Application failed: %s", str(e), exc_info=True)
            self._shutdown()
            sys.exit(1)

    def _run_uvicorn(self):
        """Run Uvicorn server with process tracking"""
        config = uvicorn.Config(
            app=app,
            host="0.0.0.0",
            port=8000,
            log_level="debug",
            access_log=True,
            timeout_keep_alive=60
        )
        server = uvicorn.Server(config)

        # Register Uvicorn worker PID
        if hasattr(server, 'serve'):
            import multiprocessing
            if isinstance(server.servers, multiprocessing.Process):
                self.process_manager.register_pid(server.servers.pid)

        server.run()

    def _monitor_activity(self):
        """Main monitoring loop"""
        while not getattr(self, '_shutdown_flag', False):
            try:
                self._log_system_status()
                time.sleep(30)
            except KeyboardInterrupt:
                self._shutdown()
            except Exception as e:
                self.logger.error("Monitor error: %s", str(e))

    def _log_system_status(self):
        """Log current system status"""
        status = {
            'uptime': time.time() - self.start_time,
            'active_jobs': len(self.scheduler.scheduler.get_jobs()) if self.scheduler else 0,
            'kafka_status': self._check_kafka()
        }
        self.logger.info("System status: %s", status)

    def _check_kafka(self):
        """Check Kafka connection status"""
        try:
            if not self.scheduler or not hasattr(self.scheduler, 'fetcher'):
                return "no_scheduler"

            producer = self.scheduler.fetcher.kafka_publisher.producer
            return "connected" if len(producer.cluster.brokers()) > 0 else "disconnected"
        except Exception as e:
            return f"error: {str(e)}"

    def _shutdown(self, signum=None, frame=None):
        """Graceful shutdown procedure"""
        if getattr(self, '_shutdown_flag', False):
            return

        self._shutdown_flag = True
        self.logger.info("Initiating shutdown sequence...")

        shutdown_start = time.time()

        # Shutdown scheduler first
        if self.scheduler:
            try:
                self.logger.info("Stopping scheduler...")
                self.scheduler.shutdown(timeout=10)
            except Exception as e:
                self.logger.error("Scheduler shutdown error: %s", str(e))

        # Then executor
        if self.executor:
            try:
                self.logger.info("Stopping executor...")
                self.executor.shutdown(wait=True, cancel_futures=True)
            except Exception as e:
                self.logger.error("Executor shutdown error: %s", str(e))

        # Force cleanup if needed
        self.process_manager.cleanup()

        shutdown_time = time.time() - shutdown_start
        self.logger.info("Shutdown completed in %.2f seconds", shutdown_time)
        sys.exit(0)

if __name__ == "__main__":
    # Handle zombie processes
    if os.name == 'posix':
        import signal as unix_signal
        unix_signal.signal(unix_signal.SIGCHLD, unix_signal.SIG_IGN)

    Application().run()
