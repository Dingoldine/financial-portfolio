from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
import time, os, shutil
import constants

patterns = "*"
ignore_patterns = ["*/*.log"]
ignore_directories = True
case_sensitive = True
my_event_handler = PatternMatchingEventHandler(patterns, ignore_patterns, ignore_directories, case_sensitive)

currentAsset = ""

def on_created(event):
    global currentAsset
    print(f"{event.src_path} has been created!")
    filename = os.path.basename(event.src_path)
    # get asset name fom latest created .txt file
    if((not ".pdf" in event.src_path) and (not ".xlsx" in event.src_path)):
        currentAsset = filename.split("_")[0]
def on_deleted(event):
    print(f"Deleted {event.src_path}!")

def on_modified(event):
    global currentAsset 
    time.sleep(2)  # wait to allow file to be fully written
    print(f"{event.src_path} has been modified")
    filename = os.path.basename(event.src_path)
    # get asset name fom latest created .txt file
    if((not ".pdf" in event.src_path) and (not ".xlsx" in event.src_path)):
        currentAsset = filename.split("_")[0]

def on_moved(event):
    print(f"{event.src_path} has been moved to {event.dest_path}")
    if(("pdf.part" in event.src_path) and (".pdf" in event.dest_path)): #PDF morningstar file download complete
        print("Download Complete!")
        global currentAsset
        oldfilename = os.path.basename(event.dest_path)
        newfilename = f'{currentAsset}.pdf'
        #rename
        print("Renaming {} to {}".format(oldfilename, newfilename))
        shutil.move(os.path.join(constants.pdfDownloadDir, oldfilename), os.path.join(constants.pdfDownloadDir, newfilename))

my_event_handler.on_created = on_created
my_event_handler.on_deleted = on_deleted
my_event_handler.on_modified = on_modified
my_event_handler.on_moved = on_moved


path = "."
go_recursively = True
my_observer = Observer()
my_observer.schedule(my_event_handler, path, recursive=go_recursively)

def startObserver(): 
    print('Starting file directory watcher...')
    my_observer.start()

    while True:
        time.sleep(1)

def stopObserver():
    print('Turning off file directory watcher...')
    my_observer.stop()
    my_observer.join()