document.addEventListener('DOMContentLoaded', function () {
    let calendar;

    const modalCalendario = document.getElementById('modalCalendarioReservas');
    if (!modalCalendario) return;

    modalCalendario.addEventListener('shown.bs.modal', function () {
        if (calendar) {
            calendar.render();
            return;
        }
        cargarCalendario();
    });

   function cargarCalendario() {
    const calendarEl = document.getElementById('calendarioReservas');

    fetch("/panel_admin/calendario/eventos/")
        .then(res => res.json())
        .then(data => {
            const eventos = Object.entries(data.fechas).map(([fecha, info]) => ({
                start: fecha,
                display: 'background',
                color: (info.pasada && !info.activa) ? '#8a8a8a' : '#0d6efd',
            }));

            calendar = new FullCalendar.Calendar(calendarEl, {
                locale: 'es',
                initialView: 'dayGridMonth',
                contentHeight: 'auto',
                events: eventos,
                dateClick: function (info) {
                    cargarHorasDelDia(info.dateStr);
                }
            });
            calendar.render();
        })
        .catch(err => console.error('Error cargando calendario:', err));
}

    function cargarHorasDelDia(fecha) {
        fetch(`/panel_admin/calendario/dia/${fecha}/`)
            .then(res => res.json())
            .then(data => {
                const contenedor = document.getElementById('listaHorasDia');
                document.getElementById('tituloHorasDia').textContent = `Reservas del ${fecha}`;
                contenedor.innerHTML = '';

                if (data.reservas.length === 0) {
                    contenedor.innerHTML = '<p class="text-white-50">No hay reservas ese día.</p>';
                } else {
                    data.reservas.forEach(r => {
                        const colorCliente = colorParaCliente(r.cliente);
                        const item = document.createElement('div');
                        item.className = 'p-2 mb-2 rounded-3';
                        item.style.cursor = 'pointer';
                        item.style.borderLeft = `4px solid ${colorCliente}`;
                        item.style.background = '#1a1a1a';
                        item.innerHTML = `<strong class="text-white">${r.hora_inicio}</strong> — 
                            <span style="color:${colorCliente}">${r.cliente}</span> 
                            <small class="text-white-50">(${r.cancha})</small>`;
                        item.onclick = () => verDetalleReserva(r.id);
                        contenedor.appendChild(item);
                    });
                }

                bootstrap.Modal.getInstance(modalCalendario)?.hide();
                new bootstrap.Modal(document.getElementById('modalHorasDia')).show();
            })
            .catch(err => console.error('Error cargando horas del día:', err));
    }

    function verDetalleReserva(id) {
        fetch(`/panel_admin/calendario/reserva/${id}/`)
            .then(res => res.json())
            .then(r => {
                document.getElementById('contenidoDetalleReserva').innerHTML = `
                    <p class="text-white"><strong>Cliente:</strong> ${r.cliente}</p>
                    <p class="text-white"><strong>Cancha:</strong> ${r.cancha}</p>
                    <p class="text-white"><strong>Fecha:</strong> ${r.fecha}</p>
                    <p class="text-white"><strong>Hora:</strong> ${r.hora}</p>
                    <p class="text-white"><strong>Duración:</strong> ${r.duracion}</p>
                    <p class="text-white"><strong>Estado:</strong> ${r.estado}</p>
                    <p class="text-white"><strong>Pago:</strong> $${r.monto_pagado}${r.saldo_pendiente ? ' pagado / $' + r.saldo_pendiente + ' pendiente' : ''}</p>
                    <p class="text-white"><strong>Teléfono:</strong> ${r.telefono}</p>
                `;
                bootstrap.Modal.getInstance(document.getElementById('modalHorasDia'))?.hide();
                new bootstrap.Modal(document.getElementById('modalDetalleReserva')).show();
            })
            .catch(err => console.error('Error cargando detalle:', err));
    }

    function colorParaCliente(nombre) {
        let hash = 0;
        for (let i = 0; i < nombre.length; i++) hash = nombre.charCodeAt(i) + ((hash << 5) - hash);
        const hue = hash % 360;
        return `hsl(${hue}, 70%, 60%)`;
    }
});