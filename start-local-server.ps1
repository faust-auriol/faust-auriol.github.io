param(
  [int]$Port = 8080
)

$root = [System.IO.Path]::GetFullPath($PSScriptRoot)
$listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $Port)
$listener.Start()

Write-Host "Portfolio disponible sur http://127.0.0.1:$Port"
Write-Host 'Appuyez sur Ctrl+C pour arrêter le serveur.'

$contentTypes = @{
  '.css' = 'text/css; charset=utf-8'
  '.html' = 'text/html; charset=utf-8'
  '.js' = 'application/javascript; charset=utf-8'
  '.json' = 'application/json; charset=utf-8'
  '.svg' = 'image/svg+xml'
}

try {
  while ($true) {
    $client = $listener.AcceptTcpClient()
    try {
      $stream = $client.GetStream()
      $reader = [System.IO.StreamReader]::new($stream, [System.Text.Encoding]::ASCII, $false, 1024, $true)
      $requestLine = $reader.ReadLine()

      while ($reader.ReadLine()) { }

      $status = '400 Bad Request'
      $body = [byte[]]@()
      $contentType = 'text/plain; charset=utf-8'
      $isHeadRequest = $false

      if ($requestLine -match '^(GET|HEAD) ([^ ]+) HTTP/') {
        $isHeadRequest = $Matches[1] -eq 'HEAD'
        $requestPath = [uri]::UnescapeDataString(($Matches[2] -split '\?')[0])
        if ($requestPath -eq '/') { $requestPath = '/index.html' }

        $relativePath = $requestPath.TrimStart('/').Replace('/', [System.IO.Path]::DirectorySeparatorChar)
        $filePath = [System.IO.Path]::GetFullPath((Join-Path $root $relativePath))
        $insideRoot = $filePath.StartsWith($root + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)

        if (-not $insideRoot) {
          $status = '403 Forbidden'
        } elseif (Test-Path -LiteralPath $filePath -PathType Leaf) {
          $status = '200 OK'
          $body = [System.IO.File]::ReadAllBytes($filePath)
          $extension = [System.IO.Path]::GetExtension($filePath).ToLowerInvariant()
          if ($contentTypes.ContainsKey($extension)) { $contentType = $contentTypes[$extension] }
        } else {
          $status = '404 Not Found'
        }
      }

      $header = "HTTP/1.1 $status`r`nContent-Type: $contentType`r`nContent-Length: $($body.Length)`r`nConnection: close`r`n`r`n"
      $headerBytes = [System.Text.Encoding]::ASCII.GetBytes($header)
      $stream.Write($headerBytes, 0, $headerBytes.Length)
      if (-not $isHeadRequest -and $body.Length -gt 0) { $stream.Write($body, 0, $body.Length) }
      $stream.Flush()
    } finally {
      $client.Dispose()
    }
  }
} finally {
  $listener.Stop()
}
