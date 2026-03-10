require 'net/http'
require 'uri'
require 'json'

uri = URI('http://justibot:8001/api/ws/webhook')
req = Net::HTTP::Post.new(uri, 'Content-Type' => 'application/json')
req.body = { event: 'ping_test' }.to_json

begin
  res = Net::HTTP.start(uri.hostname, uri.port) do |http|
    http.request(req)
  end
  puts "STATUS: #{res.code}"
  puts "BODY: #{res.body}"
rescue => e
  puts "ERROR: #{e.message}"
end
