# rss_feeder/__main__.py
import signal
import logging
import time
import sys
from concurrent.futures import ThreadPoolExecutor
import uvicorn
from rss_feeder.scheduler import FeedScheduler
from rss_feeder.health import app as health_app

class Application:
    def __init__(self):
        self.scheduler = None
        self.executor = None
        self._shutdown_flag = False
        configure_logging()
        self.logger = logging.getLogger('main')

    def run(self):
        try:
            self.scheduler = FeedScheduler()
            self.executor = ThreadPoolExecutor(max_workers=2)
            
            # Register signal handlers first
            signal.signal(signal.SIGINT, self._shutdown)
            signal.signal(signal.SIGTERM, self._shutdown)
            
            # Start services
            self.executor.submit(self._start_health_server)
            self.scheduler.start()
            self.logger.info("Application started successfully")
            
            # Main loop
            while not self._shutdown_flag:
                time.sleep(1)
                
        except Exception as e:
            self.logger.error("Application failed: %s", str(e))
            self._shutdown()
            sys.exit(1)

    def _start_health_server(self):
        """Start health server with error handling"""
        try:
            config = uvicorn.Config(
                app=health_app,
                host="0.0.0.0",
                port=8000,
                log_level="info",
                access_log=False
            )
            server = uvicorn.Server(config)
            server.run()
        except Exception as e:
            self.logger.error("Health server failed: %s", str(e))
            self._shutdown()

    def _shutdown(self, signum=None, frame=None):
        """Graceful shutdown procedure"""
        if self._shutdown_flag:  # Already shutting down
            return
            
        self._shutdown_flag = True
        self.logger.info("Shutdown initiated")
        
        try:
            if self.scheduler:
                self.logger.info("Shutting down scheduler...")
                self.scheduler.shutdown()
        except Exception as e:
            self.logger.error("Error shutting down scheduler: %s", str(e))
            
        try:
            if self.executor:
                self.logger.info("Shutting down thread pool...")
                self.executor.shutdown(wait=True)
        except Exception as e:
            self.logger.error("Error shutting down executor: %s", str(e))
            
        self.logger.info("Application shutdown complete")
        sys.exit(0)

def configure_logging():
    """Setup application logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('rss_feeder.log')
        ]
    )

if __name__ == "__main__":
    Application().run()
