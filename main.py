from dotenv import load_dotenv

import structlog


from runner.runner import Runner

log = structlog.get_logger()

load_dotenv(override=True)


def main():
    log.info("Let's go!")
    Runner.get_instance().run()


if __name__ == "__main__":
    main()
