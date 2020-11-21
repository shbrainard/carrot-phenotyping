import click
import lensfunpy


def list_cameras():
    database = lensfunpy.Database()
    for camera in database.cameras:
        camera_string = "Maker: %s \t Model: %s" % (camera.maker, camera.model)
        click.echo(camera_string)


def list_lenses():
    database = lensfunpy.Database()
    for lense in database.lenses:
        lense_string = "Maker: %s \t Model: %s" % (lense.maker, lense.model)
        click.echo(lense_string)


@click.command()
@click.option("--cameras", is_flag=True)
@click.option("--lenses", is_flag=True)
def run(cameras, lenses):
    if cameras:
        list_cameras()
        return
    if lenses:
        list_lenses()
        return


if __name__ == "__main__":
    run()
