// ** Page elements

const url_input = document.getElementById('urlInput');
const my_iframe = document.getElementById('myIframe');
const pdb_inspect_button = document.getElementById('pdbInspectButton');
const pdb_reset_button = document.getElementById('pdbResetButton');
const filter_reset_button = document.getElementById('filterResetButton');
const sidebar = document.querySelector('.sidebar');
const sidebar_toggle_button = document.getElementById('sidebarToggleButton');
const alert_message_box = document.getElementById('loadedAlert');
var selector = {
  'model': document.getElementById('modelSelector'),
  'pdbid': document.getElementById('pdbidSelector'),
  'organism': document.getElementById('filterOrganismSelector'),
  'jh': document.getElementById('filterJhSelector'),
  'jl': document.getElementById('filterJlSelector'),
  'vh': document.getElementById('filterVhSelector'),
  'vl': document.getElementById('filterVlSelector'),
};
var selector_fn = {
  'model': null,
  'pdbid': null,
  'organism': null,
  'jh': null,
  'jl': null,
  'vh': null,
  'vl': null,
};

// ** Data

const github_paths = [
  `https://raw.githubusercontent.com/davidrich27/gcreplay-viz/`,
]
const github_path = github_paths[0];
const summary_path = `${github_path}/metadata/summary.json`;
var summary_db = null;

const sidebar_btn_txt = {
  'open': `<<<`,
  'close': `>>>`
};

// Template for dms-viz.github.io query string.
// For query string arguments, see `dms-viz.github.io/v0/js/tool.js:638-696`
var dms_viz_request = {
  'name': null,    /* name displayed at top graph */
  'data': null,    /* url path to json file */
  'pr': 'cartoon', /* focal protein representation */
  'pc': '#b2df8a', /* focal protein chain color */
  'br': 'cartoon', /* peripheral (background) protein representation */
  'bc': '#66ccee', /* peripheral (background) protein chain color */
  'sc': '#ffffff', /* screen color */
  //  'ce': '%5B%22DNSM%22%5D',
};

// ** Functions

class HTMLHelper {
  static raw(text) {
    return `${text}\n`
  }

  static p(text) {
    return `<p>${text}</p>\n`
  }

  static ul_open() {
    return `<ul>\n`
  }

  static ul_close() {
    return `</ul>\n`
  }

  static li(text) {
    return `<li>${text}</li>\n`
  }

  static hr() {
    return `<hr />`
  }

  static ul(text_list) {
    var html_str = HTMLHelper.ul_open();
    for (const i in text_list) {
      const text = text_list[i];
      html_str += HTMLHelper.li(text);
    }
    html_str += HTMLHelper.ul_close();
    return html_str;
  }

  static option_list(opt_values, opt_prompt = null) {
    var select_options = ``
    if (opt_prompt != null) {
      select_options += `\n<option selected>${opt_prompt}: ${opt_values.length}</option>\n`;
    }
    for (const i in opt_values) {
      const value = opt_values[i];
      const select_option = `<option value=\'${value}\'>${value}</option> \n`;
      select_options += select_option;
    }
    return select_options;
  }
}

class Utility {
  static log(text, do_log = true) {
    if (do_log) {
      console.log(`${text}`);
    }
  }

  static load_json(url_path) {
    return new Promise((resolve, reject) => {
      fetch(url_path)
        .then(response => {
          if (!response.ok) {
            throw new Error('Network response was not ok');
          }
          return response.json();
        })
        .then(json_data => {
          resolve(json_data);
        })
        .catch(error => {
          reject(error);
        });
    });

  }

  static async load_summary() {
    summary_db = await Utility.load_json(summary_path);
    summary_db = new JsonTable(summary_db, 'row');
    return summary_db;
  }

  static iota(length, start = 0, step = 1) {
    const result = [];
    for (let i = 0; i < length; i++) {
      result.push(start + i * step);
    }
    return result;
  }

  static create_unique_sorted_array(arr) {
    const unique_values = new Set(arr);
    const sorted_array = Array.from(unique_values).sort();
    return sorted_array;
  }

  static create_query_string(obj) {
    let query_params = [];
    for (let key in obj) {
      if (obj.hasOwnProperty(key)) {
        query_params.push(encodeURIComponent(key) + '=' + encodeURIComponent(obj[key]));
      }
    }
    return query_params.join('&');
  }

  static truncate(str, delim = '*') {
    return str.split(delim)[0];
  }

  static check_file_exists(file_url, do_log = false) {
    var http = new XMLHttpRequest();
    http.open('HEAD', file_url, false);
    http.send();
    if (http.status === 200) {
      Utility.log(`File exists: ${file_url}`, do_log);
      return true;
    } else {
      Utility.log(`File does NOT exist: ${file_url}`, do_log);
      return false;
    }
  }

  static query_matches(data, query) {
    var is_found = false;
    var split_data = data.split(',')
    for (const i in split_data) {
      const sub_data = split_data[i];
      if (query == sub_data) {
        is_found = true;
        break;
      }
    }
    return is_found;
  }
}

class JsonTable {
  constructor(json_obj, ordered_by = 'col') {
    this.data = json_obj;
    // ordered_by can be ordered first by 'col' or 'row'.
    this.ordered_by = ordered_by;
    this.initialize();
  }

  initialize() {
    this.all_values_by_field = {};
    this.selected_values_by_field = {};
    this.fields = this.get_fields();
    // initialize all fields and selected fields.
    this.all_rowids = this.get_all_rowids();
    this.selected_rowids = this.all_rowids;
    for (const i in this.fields) {
      const field = this.fields[i];
      this.all_values_by_field[field] = this.get_unique_values_by_field(field);
    }
    this.reset_filter();
  }

  get_fields() {
    if (this.ordered_by == 'col') {
      return Object.keys(this.data);
    } /* else if (this.ordered_by == 'row') */
    return Object.keys(this.data[0]);
  }

  get_all_rowids() {
    if (this.ordered_by == 'col') {
      return Object.keys(this.data.pdbid);
    } /* else if (this.orientation == 'row) */
    return Object.keys(this.data);
  }

  get_data(row_id, field_name) {
    if (this.ordered_by == 'col') {
      return this.data[field_name][row_id];
    } /* else if (this.ordered_by == 'row') */
    return this.data[row_id][field_name];
  }

  get_row_data(row_id) {
    var row_data = {};
    for (const i in this.fields) {
      const field_name = this.fields[i];
      row_data[field_name] = this.get_data(row_id, field_name);
    }
    return row_data;
  }

  find_first_row_by_query(field_name, query) {
    for (const i in this.selected_rowids) {
      const row_id = this.selected_rowids[i];
      const data = this.get_data(row_id, field_name);
      if (Utility.query_matches(data, query)) {
        return this.get_row_data(row_id);
      }
    }
    return null;
  }

  reset_filter() {
    this.selected_rowids = this.all_rowids;
    for (const i in this.fields) {
      const field = this.fields[i];
      this.selected_values_by_field[field] = this.all_values_by_field[field];
    }
  }

  update_after_filter() {
    for (const i in this.fields) {
      const field = this.fields[i];
      this.selected_values_by_field[field] = this.get_unique_values_by_field(field);
    }
  }

  apply_filter(field_name, query, update_fields = true) {
    var new_selected_rowids = []
    for (const i in this.selected_rowids) {
      const row_id = this.selected_rowids[i];
      const data = this.get_data(row_id, field_name);
      if (Utility.query_matches(data, query)) {
        new_selected_rowids.push(row_id);
      }
    }
    this.selected_rowids = new_selected_rowids;
    if (update_fields) {
      this.update_after_filter();
    }
    return this.selected_rowids;
  }

  get_values_by_field(field_name) {
    var values = [];
    for (const i in this.selected_rowids) {
      const row_id = this.selected_rowids[i];
      var data = this.get_data(row_id, field_name);
      // data = Utility.truncate(data, '*');
      values.push(data);
    }
    return values;
  }

  get_unique_values_by_field(field_name) {
    var vals = this.get_values_by_field(field_name);
    return Utility.create_unique_sorted_array(vals);
  }
}

class Event {
  static sidebar_toggle() {
    sidebar.classList.toggle('sidebar-collapse');
    sidebar_toggle_button.innerText = (sidebar_toggle_button.innerText == sidebar_btn_txt['open']) ? sidebar_btn_txt['close'] : sidebar_btn_txt['open'];
  }

  static alert_set_text(text, append = false, alert_color = null) {
    if (append) {
      alert_message_box.innerHTML += HTMLHelper.hr();
    } else {
      alert_message_box.innerHTML = '';
    }
    alert_message_box.innerHTML += HTMLHelper.p(load_status);

    if (alert_color) {
      Event.alert_color(alert_color);
    }
  }

  static alert_set_color(alert_color) {
    if (alert_color != null) {
      alert_message_box.classList.remove('alert-danger');
      alert_message_box.classList.remove('alert-warning');
      alert_message_box.classList.remove('alert-success');
      alert_message_box.classList.add(alert_color);
    }
  }

  static find_data_path(data_name) {
    for (const i in github_paths) {
      var github_path = github_paths[i];
      var data_path = `${github_path}/data/${data_name}`;
      var file_exists = Utility.check_file_exists(data_path);
      if (file_exists) {
        return data_path;
      }
    }
    return null;
  }

  static submit_dms_viz_request(request = dms_viz_request) {
    var query_string = Utility.create_query_string(request);
    var url = `https://dms-viz.github.io/v0/?${query_string}`;
    console.log(`Loading url into iframe: ${url}`);
    my_iframe.src = url;
  }

  static load_pdb_from_query_string() {
    const url = new URL(window.location.href);
    const params = new URLSearchParams(url.search.toLowerCase());
    console.log(params);
    var is_pdb_loaded = false;
    if (query_pdbid) {
      is_pdb_loaded = Event.load_pdb(query_pdbid);
      if (!is_pdb_loaded) {
        alert_message_box.innerText = `PDBID requested from querystring does not exist: ${query_pdbid}.`;
        alert_message_box.classList.add('alert-danger');
      }
    }
    return is_pdb_loaded;
  }
}

// ** Event Listeners

document.addEventListener('DOMContentLoaded', async function () {
  // Initialize page elements
  sidebar_toggle_button.innerText = sidebar_btn_txt['open']

  // Initialize data
  summary_db = await Utility.load_summary();
  summary_db = new JsonTable(summary_db, 'row');

  // Initialize filters
  Event.model_repopulate();
  Event.filter_repopulate_all();

  // Add events
  pdb_inspect_button.addEventListener('click', Event.pdb_inspect);
  pdb_reset_button.addEventListener('click', Event.pdb_reset);

  for (const i in filter_fields) {
    const field = filter_fields[i];
    selector_fn[field] = function (event) {
      index = event.target.selectedIndex;
      value = event.target.value;
      Event.filter_update(field, value);
    };
    selector[field].addEventListener('change', selector_fn[field]);
  }

  fields = ['pdbid', 'model']
  fields_disable = [false, true]
  for (const i in fields) {
    const field = fields[i];
    selector_fn[field] = function (event) {
      index = event.target.selectedIndex;
      value = event.target.value;
      selected[field] = value;
      Event.filter_set_active(field, fields_disable[i]);
    };
    selector[field].addEventListener('change', selector_fn[field]);
  }

  // Set default model
  default_model = 'DNSM';
  selector['model'].value = default_model;
  selected['model'] = default_model;
  Event.filter_set_active('model', true);

  // Set to pdb in query string
  var is_pdb_loaded = Event.load_pdb_from_query_string()
  console.log(`is_pdb_loaded: ${is_pdb_loaded}`)
  if (!is_pdb_loaded) {
    value = '6mtx';
    selector['pdbid'].value = value;
    selected['pdbid'] = value;
    Event.filter_set_active('pdbid');
    pdb_inspect_button.click();
    // pdb_reset_button.click();
  }
});







