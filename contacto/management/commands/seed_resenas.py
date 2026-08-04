from django.core.management.base import BaseCommand
from contacto.models import Resena


RESENAS_BASE = [
    {
        "nombre": "Carlos Ramírez",
        "jugador": "Amateur",
        "cancha": "Fútbol 5",
        "estrellas": 5,
        "texto": "Excelente cancha, muy bien mantenida y la reserva fue súper fácil.",
    },
    {
        "nombre": "Laura Gómez",
        "jugador": "Semi-profesional",
        "cancha": "Fútbol 7",
        "estrellas": 4,
        "texto": "Buena experiencia, el césped sintético está en muy buen estado.",
    },
    {
        "nombre": "Andrés Torres",
        "jugador": "Profesional",
        "cancha": "Fútbol 11",
        "estrellas": 5,
        "texto": "Ideal para entrenamientos serios, iluminación excelente de noche.",
    },
    {
        "nombre": "Mariana López",
        "jugador": "Amateur",
        "cancha": "Fútbol 5",
        "estrellas": 4,
        "texto": "Nos encantó jugar acá con mis amigas, muy recomendado.",
    },
    {
        "nombre": "Julián Restrepo",
        "jugador": "Semi-profesional",
        "cancha": "Fútbol 7",
        "estrellas": 5,
        "texto": "El proceso de pago fue rápido y sin complicaciones.",
    },
]


class Command(BaseCommand):
    help = "Carga reseñas de ejemplo en la base de datos (solo si no hay ninguna)"

    def handle(self, *args, **options):
        if Resena.objects.exists():
            self.stdout.write(self.style.WARNING(
                "Ya existen reseñas en la base de datos. No se cargó nada para evitar duplicados."
            ))
            return

        creadas = 0
        for data in RESENAS_BASE:
            Resena.objects.create(**data)
            creadas += 1

        self.stdout.write(self.style.SUCCESS(f"{creadas} reseñas de ejemplo creadas correctamente."))