from django.core.management.base import BaseCommand

from reservas.utils import cancelar_reservas_vencidas


class Command(BaseCommand):
    help = "Cancela las reservas pendientes con más de 15 minutos sin pago."

    def handle(self, *args, **options):
        n = cancelar_reservas_vencidas()
        self.stdout.write(self.style.SUCCESS(f"Reservas canceladas por falta de pago: {n}"))