from .botcompile import build_updater
#import logging
#logging.basicConfig(level=logging.DEBUG,
#                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


def main():
    updater = build_updater()

    updater.start_polling()
    updater.idle()  # blocks

if __name__ == '__main__':
    main()