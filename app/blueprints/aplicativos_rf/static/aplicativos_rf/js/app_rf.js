(function () {
  const demos = {
    sparams: {
      'sparams-magnitude_value': '0.5',
      'sparams-magnitude_unit': 'linear',
      'sparams-phase_deg': '45'
    },
    vswr: {
      'vswr-input_kind': 'vswr',
      'vswr-value': '1.25'
    },
    dblinear: {
      'dblinear-direction': 'db_to_lin',
      'dblinear-magnitude_kind': 'amplitude',
      'dblinear-value': '-3'
    },
    microstrip: {
      'microstrip-relative_permittivity': '4.3',
      'microstrip-target_impedance': '50',
      'microstrip-substrate_height_value': '1.6',
      'microstrip-substrate_height_unit': 'mm',
      'microstrip-conductor_thickness_value': '0.035',
      'microstrip-conductor_thickness_unit': 'mm'
    },
    waveguide: {
      'waveguide-mode': 'TE',
      'waveguide-index_m': '1',
      'waveguide-index_n': '0',
      'waveguide-dimension_a_value': '22.86',
      'waveguide-dimension_a_unit': 'mm',
      'waveguide-dimension_b_value': '10.16',
      'waveguide-dimension_b_unit': 'mm',
      'waveguide-frequency_value': '10',
      'waveguide-frequency_unit': 'ghz'
    },
    lines: {
      'lines-mode': 'length_to_phase',
      'lines-frequency_value': '100',
      'lines-frequency_unit': 'mhz',
      'lines-length_value': '2.5',
      'lines-length_unit': 'm',
      'lines-phase_value': '90',
      'lines-velocity_factor': '0.82',
      'lines-eps_eff': ''
    },
    cables: {
      'cables-frequency_value': '500',
      'cables-frequency_unit': 'mhz',
      'cables-length_value': '80',
      'cables-length_unit': 'm',
      'cables-connectors_losses': '0.20,0.15'
    },
    knife: {
      'knife-frequency_value': '2.4',
      'knife-frequency_unit': 'ghz',
      'knife-d1_value': '5000',
      'knife-d1_unit': 'm',
      'knife-d2_value': '6500',
      'knife-d2_unit': 'm',
      'knife-tx_height': '35',
      'knife-rx_height': '28',
      'knife-obstacle_height': '55'
    }
  };

  document.querySelectorAll('.btn-demo').forEach(function (btn) {
    btn.addEventListener('click', function () {
      const calc = btn.dataset.demo;
      const form = btn.closest('article').querySelector('form');
      if (!form) return;
      const payload = demos[calc];
      if (!payload) return;
      Object.entries(payload).forEach(function ([name, value]) {
        const input = form.querySelector('[name="' + name + '"]');
        if (!input) return;
        if (input.tagName === 'SELECT') {
          if (value === '__first__') {
            if (input.options.length > 0) {
              input.value = input.options[0].value;
            }
          } else {
            input.value = value;
          }
        } else {
          input.value = value;
        }
      });
      if (calc === 'cables') {
        const cableSelect = form.querySelector('[name="cables-cable_id"]');
        if (cableSelect && cableSelect.options.length > 0) {
          cableSelect.value = cableSelect.options[0].value;
        }
      }
    });
  });

  document.querySelectorAll('.btn-copy').forEach(function (btn) {
    btn.addEventListener('click', function () {
      const targetSelector = btn.dataset.copy;
      const target = targetSelector ? document.querySelector(targetSelector) : null;
      if (!target) return;
      const raw = target.innerText.trim();
      if (!raw) return;
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(raw).then(function () {
          btn.classList.add('copied');
          setTimeout(function () { btn.classList.remove('copied'); }, 1200);
        });
      } else {
        const temp = document.createElement('textarea');
        temp.value = raw;
        document.body.appendChild(temp);
        temp.select();
        document.execCommand('copy');
        document.body.removeChild(temp);
      }
    });
  });
})();
