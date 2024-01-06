mod fps;
use bevy::prelude::*;
use fps::FPSPlugin;


fn add_camera(mut commands: Commands) {
    commands.spawn(Camera2dBundle::default());
}

fn main() {
    App::new()
        .insert_resource(ClearColor(Color::rgb(0.4, 0.6, 0.6)))
        .add_systems(Startup, add_camera)
        .add_plugins((DefaultPlugins, FPSPlugin))
        .run();
}
