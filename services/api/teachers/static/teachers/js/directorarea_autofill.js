(function () {
    'use strict';

    function fillFromDocente(id) {
        if (!id) return;
        fetch('/admin/teachers/directorarea/docente-data/?id=' + id, {
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                var fields = { nombre: data.nombre, area: data.area, telefono: data.telefono, correo: data.correo };
                Object.keys(fields).forEach(function (f) {
                    var el = document.querySelector('#id_' + f);
                    if (el && fields[f]) el.value = fields[f];
                });
            });
    }

    document.addEventListener('DOMContentLoaded', function () {
        var $ = window.django && window.django.jQuery;
        var select = document.querySelector('#id_docente');
        if (!select) return;

        if ($) {
            // El widget autocomplete (Select2) dispara 'change' como evento de
            // jQuery, no como evento nativo del DOM: addEventListener no lo capta.
            $(select).on('change', function () {
                fillFromDocente(select.value);
            });
        } else {
            // Sin jQuery (select simple sin Select2), el evento nativo sí sirve.
            select.addEventListener('change', function () {
                fillFromDocente(select.value);
            });
        }
    });
})();
