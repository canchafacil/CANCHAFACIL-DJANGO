from datetime import date, timedelta, time

from django.core.management.base import BaseCommand
from django.utils import timezone

from usuarios.models import Usuario
from gestion_canchas.models import Cancha
from reservas.models import Reserva
from comunidad.models import PartidoAbierto, Reto, PublicacionMuro


class Command(BaseCommand):
    help = 'Crea datos de ejemplo para probar la sección Comunidad (usando canchas reales ya cargadas)'

    def _crear_reserva_demo(self, usuario, cancha, fecha, hora_str, correo):
        """Crea una reserva confirmada y pagada por completo, lista para publicar."""
        h, m = map(int, hora_str.split(':'))
        reserva = Reserva.objects.create(
            nombre=f'{usuario.first_name} {usuario.last_name}',
            correo=correo,
            telefono='3000000000',
            fecha=fecha,
            hora=time(h, m),
            horas=[hora_str],
            cancha=cancha.nombre,
            duracion='60 min',
            estado=Reserva.ESTADO_CONFIRMADA,
            tipo_pago=Reserva.TIPO_PAGO_COMPLETO,
        )
        total = reserva.calcular_total()
        reserva.precio_total = total
        reserva.monto_pagado = total
        reserva.saldo_pendiente = 0
        reserva.save(update_fields=['precio_total', 'monto_pagado', 'saldo_pendiente'])
        return reserva

    def handle(self, *args, **options):
        hoy = date.today()

        # ---- Usuarios demo ----
        demo_users = [
            {'first_name': 'Carlos', 'last_name': 'Pérez', 'email': 'carlos.demo@canchafacil.com'},
            {'first_name': 'Laura', 'last_name': 'Gómez', 'email': 'laura.demo@canchafacil.com'},
            {'first_name': 'Andrés', 'last_name': 'Ruiz', 'email': 'andres.demo@canchafacil.com'},
        ]
        usuarios = []
        for d in demo_users:
            u, creado = Usuario.objects.get_or_create(
                email=d['email'],
                defaults={
                    'first_name': d['first_name'],
                    'last_name': d['last_name'],
                    'phone': '3000000000',
                    'password': 'demo1234',
                    'rol': 'CLIENTE',
                    'activo': True,
                }
            )
            usuarios.append(u)
            if creado:
                self.stdout.write(self.style.SUCCESS(f'Usuario creado: {d["email"]} / demo1234'))

        # ---- Usa canchas REALES ya cargadas, no crea canchas propias ----
        canchas_reales = list(Cancha.objects.filter(disponible=True)[:2])
        if not canchas_reales:
            self.stdout.write(self.style.ERROR(
                'No hay canchas disponibles en la base de datos. '
                'Cargá al menos una cancha real desde el admin antes de correr este comando.'
            ))
            return

        cancha1 = canchas_reales[0]
        cancha2 = canchas_reales[1] if len(canchas_reales) > 1 else canchas_reales[0]

        # ---- Partidos abiertos demo ----
        if not PartidoAbierto.objects.exists():
            r1 = self._crear_reserva_demo(usuarios[0], cancha1, hoy, '19:00', usuarios[0].email)
            PartidoAbierto.objects.create(
                reserva=r1, cancha=cancha1, fecha=r1.fecha, hora_texto='7:00 PM – 8:00 PM',
                jugadores_faltan=3, creador=usuarios[0], cobra=False, valor=0,
            )

            r2 = self._crear_reserva_demo(usuarios[1], cancha2, hoy + timedelta(days=1), '18:00', usuarios[1].email)
            p2 = PartidoAbierto.objects.create(
                reserva=r2, cancha=cancha2, fecha=r2.fecha, hora_texto='6:00 PM – 7:00 PM',
                jugadores_faltan=2, creador=usuarios[1], cobra=True, valor=10000,
            )
            p2.participantes.add(usuarios[2])
            p2.jugadores_faltan -= 1
            p2.save(update_fields=['jugadores_faltan'])
            self.stdout.write(self.style.SUCCESS('Partidos de ejemplo creados'))

        # ---- Retos demo ----
        if not Reto.objects.exists():
            r3 = self._crear_reserva_demo(usuarios[0], cancha1, hoy + timedelta(days=2), '17:00', usuarios[0].email)
            Reto.objects.create(
                reserva=r3, equipo='Los Tigres FC', cancha=cancha1,
                horario=f'{r3.fecha.strftime("%d/%m/%Y")} 5:00 PM – 6:00 PM',
                creador=usuarios[0], cobra=False, valor=0,
            )

            r4 = self._crear_reserva_demo(usuarios[1], cancha2, hoy + timedelta(days=3), '10:00', usuarios[1].email)
            Reto.objects.create(
                reserva=r4, equipo='Dragones FC', cancha=cancha2,
                horario=f'{r4.fecha.strftime("%d/%m/%Y")} 10:00 AM – 11:00 AM',
                creador=usuarios[1], aceptado=True, aceptado_por=usuarios[2],
                cobra=True, valor=15000,
            )
            self.stdout.write(self.style.SUCCESS('Retos de ejemplo creados'))

        # ---- Muro demo ----
        if not PublicacionMuro.objects.exists():
            PublicacionMuro.objects.create(
                usuario=usuarios[0], nombre_mostrar='Grupo de los sábados',
                texto='¡Ganamos 5-3 en Arena Norte! Gran partido con los pibes 🔥'
            )
            PublicacionMuro.objects.create(
                usuario=usuarios[1], nombre_mostrar='Equipo Halcones',
                texto='Primera vez jugando en SportPlex, la cancha impecable ⚽'
            )
            self.stdout.write(self.style.SUCCESS('Publicaciones de muro creadas'))

        self.stdout.write(self.style.SUCCESS('¡Listo! Iniciá sesión con cualquiera de los correos demo y contraseña demo1234'))