#!/usr/bin/env ruby
# frozen_string_literal: true

require 'json'
require 'fileutils'
require 'open3'
require 'optparse'
require 'shellwords'
require 'yaml'

class Log
  COLORS = {
    info: "\e[36m",
    warn: "\e[33m",
    error: "\e[31m",
    reset: "\e[0m"
  }.freeze

  def initialize(io: $stderr)
    @io = io
    @use_color = @io.tty? && ENV['NO_COLOR'].nil?
  end

  def info(message)
    write('INFO', message, :info)
  end

  def warn(message)
    write('WARN', message, :warn)
  end

  def error(message)
    write('ERROR', message, :error)
  end

  private

  def write(level, message, color_key)
    timestamp = Time.now.strftime('%Y-%m-%d %H:%M:%S')
    prefix = "[#{timestamp}] #{level}"
    if @use_color
      prefix = "#{COLORS[color_key]}#{prefix}#{COLORS[:reset]}"
    end
    @io.puts("#{prefix} #{message}")
  end
end

LOGGER = Log.new

options = {
  docs_file: nil,
  project_dir: nil,
  relation: nil,
  schema: nil,
  partition_filter: nil,
  database: nil,
  target: nil,
  profiles_dir: nil,
  limit: nil,
  sample_percent: nil,
  dbt_cmd: nil,
  debug: false,
  profile_relation: nil,
  profile_schema: nil,
  profile_database: nil,
  schema_file: nil,
  source: nil,
  source_table: nil,
  dbt_args: nil,
  skip_preview: false,
  skip_profile: false
}

OptionParser.new do |opts|
  opts.banner = 'Usage: update_docs_assets.rb [options]'

  opts.on('--docs-file PATH', 'Docs markdown file to update (optional)') do |value|
    options[:docs_file] = value
  end
  opts.on('--project-dir PATH', 'dbt project directory (required)') do |value|
    options[:project_dir] = value
  end

  opts.on('--relation NAME', 'Preview relation name (required)') do |value|
    options[:relation] = value
  end
  opts.on('--schema NAME', 'Preview schema name (required)') do |value|
    options[:schema] = value
  end
  opts.on('--partition-filter FILTER', "Preview partition filter or 'none' (required)") do |value|
    options[:partition_filter] = value
  end
  opts.on('--database NAME', 'Preview database/project name') do |value|
    options[:database] = value
  end
  opts.on('--target NAME', 'dbt target name') do |value|
    options[:target] = value
  end
  opts.on('--profiles-dir PATH', 'dbt profiles directory') do |value|
    options[:profiles_dir] = value
  end
  opts.on('--limit N', 'Preview row limit') do |value|
    options[:limit] = value
  end
  opts.on('--sample-percent N', 'Preview TABLESAMPLE percent') do |value|
    options[:sample_percent] = value
  end
  opts.on('--dbt-cmd CMD', 'dbt command (overrides PATH/DBT_CMD)') do |value|
    options[:dbt_cmd] = value
  end
  opts.on('--debug', 'Enable debug logging for preview') do
    options[:debug] = true
  end

  opts.on('--profile-relation NAME', 'Profile relation name (required)') do |value|
    options[:profile_relation] = value
  end
  opts.on('--profile-schema NAME', 'Profile schema name (required)') do |value|
    options[:profile_schema] = value
  end
  opts.on('--profile-database NAME', 'Profile database/project name') do |value|
    options[:profile_database] = value
  end
  opts.on('--schema-file PATH', 'Schema YAML file to update (required)') do |value|
    options[:schema_file] = value
  end
  opts.on('--source NAME', 'Source name in schema.yml') do |value|
    options[:source] = value
  end
  opts.on('--source-table NAME', 'Source table name (defaults to relation)') do |value|
    options[:source_table] = value
  end
  opts.on('--dbt-args ARGS', 'Extra args to pass to dbt for profiling') do |value|
    options[:dbt_args] = value
  end

  opts.on('--skip-preview', 'Skip preview update') do
    options[:skip_preview] = true
  end
  opts.on('--skip-profile', 'Skip profile update') do
    options[:skip_profile] = true
  end
end.parse!

required = %i[project_dir relation schema partition_filter profile_relation profile_schema schema_file]
missing = required.select { |key| options[key].nil? || options[key].to_s.strip.empty? }
unless missing.empty?
  LOGGER.error("missing required args: #{missing.join(', ')}")
  exit 1
end

def run_dbt(cmd)
  LOGGER.info("running #{Shellwords.join(cmd)}")
  stdout, stderr, status = Open3.capture3(*cmd)
  [stdout, stderr, status]
end

def normalize_partition_filter(value)
  return nil if value.nil?
  normalized = value.strip
  return nil if %w[none null].include?(normalized.downcase)
  normalized
end

def markdown_escape(value)
  text = value.nil? ? 'null' : value.to_s
  text.gsub('|', '\\|').gsub("\n", ' ')
end

def build_preview_table(rows)
  columns = rows.empty? ? [] : rows.first.keys
  return '_No rows returned._' if columns.empty?

  header = "| #{columns.map { |c| markdown_escape(c) }.join(' | ')} |"
  separator = "| #{columns.map { '---' }.join(' | ')} |"
  body = rows.map do |row|
    cells = columns.map { |col| markdown_escape(row[col]) }
    "| #{cells.join(' | ')} |"
  end
  ([header, separator] + body).join("\n")
end

def build_combined_table(rows, profile_columns, name_map = nil)
  preview_columns = rows.empty? ? [] : rows.first.keys
  profile_map = {}
  profile_columns.each { |col| profile_map[col['name'].to_s.downcase] = col }

  if preview_columns.empty? && !profile_map.empty?
    preview_columns = profile_columns.map do |col|
      mapped = name_map ? name_map[col['name'].to_s.downcase] : nil
      mapped || col['name']
    end
  end

  return '_No rows returned._' if preview_columns.empty?

  header = "|  | #{preview_columns.map { |c| markdown_escape(c) }.join(' | ')} |"
  separator = "| #{(['---'] * (preview_columns.length + 1)).join(' | ')} |"

  preview_rows = rows.map do |row|
    cells = preview_columns.map { |col| markdown_escape(row[col]) }
    "|  | #{cells.join(' | ')} |"
  end
  blank_row = "|  | #{([''] * preview_columns.length).join(' | ')} |"

  profile_metrics = [
    ['data_type', ->(meta) { meta['data_type'] }],
    ['row_count', ->(meta) { meta['row_count'] }],
    ['not_null_%', ->(meta) { format_percent(meta['not_null_proportion']) }],
    ['distinct_%', ->(meta) { format_percent(meta['distinct_proportion']) }],
    ['distinct_count', ->(meta) { meta['distinct_count'] }],
    ['min', ->(meta) { meta['min'] }],
    ['max', ->(meta) { meta['max'] }],
    ['avg', ->(meta) { meta['avg'] }],
    ['median', ->(meta) { meta['median'] }],
    ['profiled_at', ->(meta) { meta['profiled_at'] }]
  ]

  profile_rows = profile_metrics.map do |label, extractor|
    values = preview_columns.map do |col_name|
      meta = profile_map[col_name.to_s.downcase] ? (profile_map[col_name.to_s.downcase]['meta'] || {}) : {}
      markdown_escape(extractor.call(meta))
    end
    "| #{label} | #{values.join(' | ')} |"
  end

  ([header, separator] + preview_rows + [blank_row] + profile_rows).join("\n")
end

def replace_block(content, start_marker, end_marker, replacement)
  pattern = /#{Regexp.escape(start_marker)}.*?#{Regexp.escape(end_marker)}/m
  if content.match?(pattern)
    content.gsub(pattern, "#{start_marker}\n#{replacement}\n#{end_marker}")
  else
    content
  end
end

def upsert_docs_section(content, doc_name, section, start_marker = nil, end_marker = nil)
  pattern = /\{\%\s*docs\s+#{Regexp.escape(doc_name)}\s*\%\}(.*?)\{\%\s*enddocs\s*\%\}/m
  if (match = content.match(pattern))
    body = match[1]
    if start_marker && end_marker
      marker_pattern = /#{Regexp.escape(start_marker)}.*?#{Regexp.escape(end_marker)}/m
      if body.match?(marker_pattern)
        body = body.gsub(marker_pattern, section)
      else
        body = "#{body.rstrip}\n\n#{section}\n"
      end
    else
      body = "#{body.rstrip}\n\n#{section}\n"
    end
    return content.sub(pattern, "{% docs #{doc_name} %}#{body}{% enddocs %}")
  end

  docs_block = "{% docs #{doc_name} %}\n" \
               "Auto-generated docs for #{doc_name}.\n\n" \
               "#{section}\n" \
               "{% enddocs %}\n"
  return docs_block if content.strip.empty?

  "#{content.rstrip}\n\n#{docs_block}"
end

def insert_preview_block(content, block)
  start_marker = '<!-- DOCS_PREVIEW_BEGIN -->'
  end_marker = '<!-- DOCS_PREVIEW_END -->'
  section = "#{start_marker}\n\n#{block}\n\n#{end_marker}"

  pattern = /#{Regexp.escape(start_marker)}.*?#{Regexp.escape(end_marker)}/m
  if content.match?(pattern)
    return content.gsub(pattern, section)
  end

  enddocs = content.index('{% enddocs %}')
  if enddocs
    return content.insert(enddocs, "#{section}\n\n")
  end

  "#{content.rstrip}\n\n#{section}\n"
end

def update_docs_preview(path, table, doc_name)
  content = File.exist?(path) ? File.read(path) : ''
  start_marker = '<!-- DOCS_PREVIEW_BEGIN -->'
  end_marker = '<!-- DOCS_PREVIEW_END -->'
  section = "#{start_marker}\n\n#{table}\n\n#{end_marker}"
  updated = upsert_docs_section(content, doc_name, section, start_marker, end_marker)
  File.write(path, updated)
  LOGGER.info("updated preview table in #{path}")
end

def format_percent(value)
  return '' if value.nil?
  number = value.to_f
  return '' if number.nan?
  format('%.1f%%', number * 100)
end

def build_profile_table(profile_columns, name_map = nil)
  headers = [
    'Column', 'Type', 'Row Count', 'Not Null %', 'Distinct %', 'Distinct Count',
    'Min', 'Max', 'Avg', 'Median', 'Profiled At'
  ]
  header_line = "| #{headers.map { |cell| markdown_escape(cell) }.join(' | ')} |"
  separator_line = "| #{headers.map { '---' }.join(' | ')} |"
  rows = profile_columns.map do |column|
    meta = column['meta'] || {}
    column_name = column['name']
    if name_map
      mapped = name_map[column_name.to_s.downcase]
      column_name = mapped if mapped
    end
    cells = [
      column_name,
      meta['data_type'] || column['data_type'],
      meta['row_count'],
      format_percent(meta['not_null_proportion']),
      format_percent(meta['distinct_proportion']),
      meta['distinct_count'],
      meta['min'],
      meta['max'],
      meta['avg'],
      meta['median'],
      meta['profiled_at']
    ]
    "| #{cells.map { |cell| markdown_escape(cell) }.join(' | ')} |"
  end
  ([header_line, separator_line] + rows).join("\n")
end

def update_docs_profile(path, profile_columns, doc_name, name_map = nil)
  content = File.exist?(path) ? File.read(path) : ''
  start_marker = '<!-- DOCS_PROFILE_BEGIN -->'
  end_marker = '<!-- DOCS_PROFILE_END -->'
  table = build_profile_table(profile_columns, name_map)
  section = "#{start_marker}\n### Profile Summary\n#{table}\n#{end_marker}"
  updated = upsert_docs_section(content, doc_name, section, start_marker, end_marker)
  File.write(path, updated)
  LOGGER.info("updated profile table in #{path}")
end

def build_column_name_map(existing_columns, preview_rows)
  name_map = {}
  preview_columns = preview_rows.empty? ? [] : preview_rows.first.keys
  preview_columns.each { |name| name_map[name.to_s.downcase] = name }
  Array(existing_columns).each do |column|
    next unless column && column['name']
    key = column['name'].to_s.downcase
    name_map[key] ||= column['name']
  end
  name_map
end

def load_schema_columns(schema_path, source_mode, source_name, source_table, model_name)
  return [] unless File.exist?(schema_path)

  data = YAML.safe_load(File.read(schema_path), aliases: true) || {}
  if source_mode
    source_entry = Array(data['sources']).find { |source| source['name'] == source_name }
    table_entry = source_entry ? Array(source_entry['tables']).find { |table| table['name'] == source_table } : nil
    return table_entry ? (table_entry['columns'] || []) : []
  end

  model_entry = Array(data['models']).find { |model| model['name'] == model_name }
  model_entry ? (model_entry['columns'] || []) : []
end

def update_schema_file(schema_path, profile_model, source_mode, source_name, source_table, model_name, doc_name, preview_rows = [])
  existing_data = File.exist?(schema_path) ? YAML.safe_load(File.read(schema_path), aliases: true) || {} : {}
  profile_columns = profile_model['columns'] || []
  added_count = 0
  doc_ref = "{{ doc('#{doc_name}') }}"
  data_type_from = lambda do |profile_column|
    profile_column['data_type'] || (profile_column['meta'] || {})['data_type']
  end

  if source_mode
    existing_data['sources'] ||= []
    source_entry = existing_data['sources'].find { |source| source['name'] == source_name }
    if source_entry.nil?
      source_entry = { 'name' => source_name, 'description' => '' }
      source_entry['tables'] = []
      existing_data['sources'] << source_entry
    end
    source_entry['tables'] ||= []
    table_entry = source_entry['tables'].find { |table| table['name'] == source_table }
    if table_entry.nil?
      table_entry = { 'name' => source_table, 'description' => '', 'columns' => [] }
      source_entry['tables'] << table_entry
    end
    if table_entry['description'].nil? || table_entry['description'].strip.empty?
      table_entry['description'] = "#{doc_ref}\n"
    elsif !table_entry['description'].include?(doc_ref)
      desc = table_entry['description'].to_s.rstrip
      table_entry['description'] = "#{desc}\n#{doc_ref}"
    end
    table_entry['columns'] ||= []
    name_map = build_column_name_map(table_entry['columns'], preview_rows)
    profile_columns.each do |profile_column|
      normalized_name = profile_column['name'].to_s.downcase
      column_name = name_map[normalized_name] || profile_column['name']
      data_type = data_type_from.call(profile_column)
      existing_column = table_entry['columns'].find { |column| column['name'].to_s.downcase == normalized_name }
      if existing_column
        existing_column['name'] = column_name if existing_column['name'] != column_name
        if existing_column['description'].nil? || existing_column['description'].empty?
          if profile_column['description'] && !profile_column['description'].empty?
            existing_column['description'] = profile_column['description']
          end
        end
        if (existing_column['data_type'].nil? || existing_column['data_type'].to_s.empty?) && data_type
          existing_column['data_type'] = data_type
        end
      else
        new_column = { 'name' => column_name, 'description' => profile_column['description'] || '' }
        new_column['data_type'] = data_type if data_type
        table_entry['columns'] << new_column
        added_count += 1
      end
    end
    LOGGER.info("updated source table #{source_name}.#{source_table} columns total=#{table_entry['columns'].length} added=#{added_count}")
  else
    existing_data['models'] ||= []
    existing_model = existing_data['models'].find { |model| model['name'] == model_name }
    if existing_model.nil?
      existing_model = { 'name' => model_name, 'description' => profile_model['description'] || '', 'columns' => [] }
      existing_data['models'] << existing_model
    end
    if existing_model['description'].nil? || existing_model['description'].strip.empty?
      existing_model['description'] = "#{doc_ref}\n"
    elsif !existing_model['description'].include?(doc_ref)
      desc = existing_model['description'].to_s.rstrip
      existing_model['description'] = "#{desc}\n#{doc_ref}"
    end
    existing_model['columns'] ||= []
    name_map = build_column_name_map(existing_model['columns'], preview_rows)
    profile_columns.each do |profile_column|
      normalized_name = profile_column['name'].to_s.downcase
      column_name = name_map[normalized_name] || profile_column['name']
      data_type = data_type_from.call(profile_column)
      existing_column = existing_model['columns'].find { |column| column['name'].to_s.downcase == normalized_name }
      if existing_column
        existing_column['name'] = column_name if existing_column['name'] != column_name
        if existing_column['description'].nil? || existing_column['description'].empty?
          if profile_column['description'] && !profile_column['description'].empty?
            existing_column['description'] = profile_column['description']
          end
        end
        if (existing_column['data_type'].nil? || existing_column['data_type'].to_s.empty?) && data_type
          existing_column['data_type'] = data_type
        end
      else
        new_column = { 'name' => column_name, 'description' => profile_column['description'] || '' }
        new_column['data_type'] = data_type if data_type
        existing_model['columns'] << new_column
        added_count += 1
      end
    end
    LOGGER.info("updated columns total=#{existing_model['columns'].length} added=#{added_count}")
  end

  output = YAML.dump(existing_data)
  output.sub!(/\A---\s*\n/, '')
  File.write(schema_path, output)
  LOGGER.info("wrote schema file #{schema_path}")
end

def ensure_docs_stub(path, doc_name)
  FileUtils.mkdir_p(File.dirname(path))
  return if File.exist?(path) && File.read(path).include?("{% docs #{doc_name} %}")

  content = "{% docs #{doc_name} %}\nAuto-generated docs for #{doc_name}.\n{% enddocs %}\n"
  if File.exist?(path)
    File.write(path, "#{content}\n#{File.read(path)}")
  else
    File.write(path, content)
  end
  LOGGER.info("created docs stub #{path}")
end


def run_preview(options)
  partition_filter = normalize_partition_filter(options[:partition_filter])
  limit = (options[:limit] || 5).to_i
  args_hash = {
    relation_name: options[:relation],
    schema: options[:schema],
    limit: limit,
    use_partition_filter: false
  }
  args_hash[:database] = options[:database] if options[:database]
  args_hash[:sample_percent] = options[:sample_percent].to_f if options[:sample_percent]
  args_hash[:partition_filter] = partition_filter if partition_filter

  dbt_cmd = options[:dbt_cmd] || ENV.fetch('DBT_CMD', 'dbt')
  cmd = Shellwords.split(dbt_cmd) + ['run-operation', 'preview_docs_rows', '--args', JSON.generate(args_hash)]
  cmd.insert(1, '--debug') if options[:debug]
  cmd += ['--project-dir', options[:project_dir]]
  cmd += ['--target', options[:target]] if options[:target]
  cmd += ['--profiles-dir', options[:profiles_dir]] if options[:profiles_dir]

  stdout, stderr, status = run_dbt(cmd)
  combined = "#{stdout}\n#{stderr}"
  if status.success?
    match = combined.match(/DOCS_PREVIEW_JSON=(.*)/)
    raise 'DOCS_PREVIEW_JSON marker not found in dbt output' unless match
    return JSON.parse(match[1].strip)
  end

  if combined.include?('TABLESAMPLE SYSTEM can only be applied directly to base tables')
    args_hash[:use_partition_filter] = true
    args_hash[:partition_filter] = partition_filter || '1=1'
    cmd = Shellwords.split(dbt_cmd) + ['run-operation', 'preview_docs_rows', '--args', JSON.generate(args_hash)]
    cmd.insert(1, '--debug') if options[:debug]
    cmd += ['--project-dir', options[:project_dir]]
    cmd += ['--target', options[:target]] if options[:target]
    cmd += ['--profiles-dir', options[:profiles_dir]] if options[:profiles_dir]
    stdout, stderr, status = run_dbt(cmd)
    combined = "#{stdout}\n#{stderr}"
    raise "dbt preview failed\nstdout:\n#{stdout}\nstderr:\n#{stderr}" unless status.success?
    match = combined.match(/DOCS_PREVIEW_JSON=(.*)/)
    raise 'DOCS_PREVIEW_JSON marker not found in dbt output' unless match
    return JSON.parse(match[1].strip)
  end

  if partition_filter
    args_hash[:use_partition_filter] = true
    cmd = Shellwords.split(dbt_cmd) + ['run-operation', 'preview_docs_rows', '--args', JSON.generate(args_hash)]
    cmd.insert(1, '--debug') if options[:debug]
    cmd += ['--project-dir', options[:project_dir]]
    cmd += ['--target', options[:target]] if options[:target]
    cmd += ['--profiles-dir', options[:profiles_dir]] if options[:profiles_dir]
    stdout, stderr, status = run_dbt(cmd)
    combined = "#{stdout}\n#{stderr}"
    raise "dbt preview failed\nstdout:\n#{stdout}\nstderr:\n#{stderr}" unless status.success?
    match = combined.match(/DOCS_PREVIEW_JSON=(.*)/)
    raise 'DOCS_PREVIEW_JSON marker not found in dbt output' unless match
    return JSON.parse(match[1].strip)
  end

  raise "dbt preview failed\nstdout:\n#{stdout}\nstderr:\n#{stderr}"
end

def run_profile(options)
  args_hash = {
    relation_name: options[:profile_relation],
    schema: options[:profile_schema]
  }
  args_hash[:database] = options[:profile_database] if options[:profile_database]

  dbt_cmd = options[:dbt_cmd] || ENV.fetch('DBT_CMD', 'dbt')
  cmd = Shellwords.split(dbt_cmd) + ['run-operation', 'print_profile_schema', '--args', JSON.generate(args_hash)]
  cmd.insert(1, '--debug') if options[:debug]
  cmd += Shellwords.split(options[:dbt_args]) if options[:dbt_args]
  cmd += ['--project-dir', options[:project_dir]]
  cmd += ['--target', options[:target]] if options[:target]
  cmd += ['--profiles-dir', options[:profiles_dir]] if options[:profiles_dir]

  stdout, stderr, status = run_dbt(cmd)
  unless status.success?
    LOGGER.error('dbt run-operation failed')
    LOGGER.warn("dbt stderr:\n#{stderr}") unless stderr.strip.empty?
    LOGGER.warn("dbt stdout:\n#{stdout}") unless stdout.strip.empty?
    exit status.exitstatus
  end

  start_index = stdout.index(/^version:\s*\d+/) || stdout.index(/^models:/)
  if start_index.nil?
    raise 'could not find YAML output from dbt'
  end

  yaml_text = stdout[start_index..]
  profile_data = YAML.safe_load(yaml_text, aliases: true) || {}
  profile_models = profile_data['models'] || []
  profile_lookup = options[:source] ? options[:profile_relation] : options[:profile_relation]
  profile_model = profile_models.find { |model| model['name'] == profile_lookup }
  raise "profile output for '#{profile_lookup}' not found" if profile_model.nil?

  profile_model
end

docs_file = options[:docs_file]
doc_name = options[:relation] || options[:profile_relation]
if docs_file.nil?
  schema_dir = File.dirname(options[:schema_file])
  docs_dir = File.join(schema_dir, 'docs')
  docs_file = File.join(docs_dir, "#{doc_name}.md")
end
options[:docs_file] = docs_file

ensure_docs_stub(options[:docs_file], doc_name)

unless options[:skip_preview]
  rows = run_preview(options)
  if options[:skip_profile]
    table = build_preview_table(rows)
    update_docs_preview(options[:docs_file], table, doc_name)
  else
    options[:_preview_rows] = rows
  end
end

unless options[:skip_profile]
  profile_model = run_profile(options)
  source_mode = !options[:source].to_s.strip.empty?
  source_table = options[:source_table] || options[:profile_relation] || options[:relation]
  existing_columns = load_schema_columns(
    options[:schema_file],
    source_mode,
    options[:source],
    source_table,
    options[:profile_relation]
  )
  name_map = build_column_name_map(existing_columns, options[:_preview_rows] || [])
  if options[:skip_preview]
    update_docs_profile(options[:docs_file], profile_model['columns'] || [], doc_name, name_map)
  else
    rows = options[:_preview_rows] || []
    combined = build_combined_table(rows, profile_model['columns'] || [], name_map)
    update_docs_preview(options[:docs_file], combined, doc_name)
  end

  update_schema_file(
    options[:schema_file],
    profile_model,
    source_mode,
    options[:source],
    source_table,
    options[:profile_relation],
    doc_name,
    options[:_preview_rows] || []
  )
end
