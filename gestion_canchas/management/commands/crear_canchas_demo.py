from django.core.management.base import BaseCommand
from gestion_canchas.models import Cancha


CANCHAS_DEMO = [
    {
        "nombre": "Complejo Deportivo Elite Bogotá",
        "tipo": "Fútbol 5",
        "descripcion": "Cancha sintética de última generación con iluminación LED y graderías techadas.",
        "precio": 90000,
        "disponible": True,
    },
    {
        "nombre": "Estadio Metropolitano Sur",
        "tipo": "Fútbol 11",
        "descripcion": "Cancha reglamentaria de césped natural, ideal para partidos oficiales y torneos.",
        "precio": 220000,
        "disponible": True,
    },
    {
        "nombre": "Cancha Los Andes Premium",
        "tipo": "Fútbol 7",
        "descripcion": "Espacio techado con vestuarios completos y zona de parqueo privado.",
        "precio": 130000,
        "disponible": True,
    },
    {
        "nombre": "Polideportivo Central Park",
        "tipo": "Fútbol 5",
        "descripcion": "Ubicada en el corazón de la ciudad, con fácil acceso y superficie antideslizante.",
        "precio": 85000,
        "disponible": True,
    },
    {
        "nombre": "Arena Fútbol La Sabana",
        "tipo": "Fútbol 7",
        "descripcion": "Complejo deportivo al aire libre con zona de descanso y cafetería.",
        "precio": 140000,
        "disponible": True,
    },
    {
        "nombre": "Club Deportivo Norte Elite",
        "tipo": "Fútbol 11",
        "descripcion": "Cancha profesional con césped sintético de alta densidad y marcador electrónico.",
        "precio": 210000,
        "disponible": True,
    },
]


class Command(BaseCommand):
    help = "Crea 6 canchas de ejemplo con nombres profesionales (no duplica si ya existen por nombre)."

    def handle(self, *args, **options):
        creadas = 0
        for datos in CANCHAS_DEMO:
            _, fue_creada = Cancha.objects.get_or_create(
                nombre=datos["nombre"],
                defaults={
                    "tipo": datos["tipo"],
                    "descripcion": datos["descripcion"],
                    "precio": datos["precio"],
                    "disponible": datos["disponible"],
                },
            )
            if fue_creada:
                creadas += 1
                self.stdout.write(self.style.SUCCESS(f'✔ Creada: {datos["nombre"]}'))
            else:
                self.stdout.write(self.style.WARNING(f'— Ya existía: {datos["nombre"]}'))

        self.stdout.write(self.style.SUCCESS(f"\nListo. {creadas} cancha(s) nueva(s) creada(s)."))