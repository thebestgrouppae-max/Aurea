<?php
// ============================================
// UPLOAD DEBUG VERSION - Mostra cada pas
// ============================================

// Configuració d'errors
error_reporting(E_ALL);
ini_set('display_errors', '1');
ini_set('log_errors', '1');
ini_set('error_log', __DIR__ . '/php_error.log');

// Augmenta límits
@ini_set('memory_limit', '256M');
@ini_set('upload_max_filesize', '20M');
@ini_set('post_max_size', '20M');
@ini_set('max_execution_time', '300');

// Inicia buffer per capturar tot
ob_start();

echo "=== DEBUG UPLOAD PHP ===\n";
echo "1. PHP s'està executant correctament\n";
echo "   - Hora servidor: " . date('Y-m-d H:i:s') . "\n";
echo "   - Memory limit: " . ini_get('memory_limit') . "\n";
echo "   - Upload max: " . ini_get('upload_max_filesize') . "\n";
echo "   - Post max: " . ini_get('post_max_size') . "\n\n";

// Headers
header('Content-Type: text/plain; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

echo "2. Headers enviats\n\n";

// Gestió OPTIONS (CORS)
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    echo "3. Petició OPTIONS (preflight CORS) - Respondent 204\n";
    http_response_code(204);
    ob_end_flush();
    exit;
}

echo "3. Mètode HTTP: " . $_SERVER['REQUEST_METHOD'] . "\n";
echo "   - Content-Type: " . ($_SERVER['CONTENT_TYPE'] ?? 'no definit') . "\n";
echo "   - Content-Length: " . ($_SERVER['CONTENT_LENGTH'] ?? 'no definit') . " bytes\n\n";

// Mostrar tots els camps rebuts
echo "4. Camps rebuts a \$_FILES:\n";
if (empty($_FILES)) {
    echo "   ⚠️  CAP FITXER REBUT!\n";
    echo "   - Possibles causes:\n";
    echo "     * FormData no s'ha enviat correctament\n";
    echo "     * El servidor ha rebutjat per límit de mida\n";
    echo "     * Content-Type incorrecte\n\n";
} else {
    foreach ($_FILES as $key => $file) {
        echo "   - Camp '$key':\n";
        echo "     * name: " . $file['name'] . "\n";
        echo "     * type: " . $file['type'] . "\n";
        echo "     * size: " . number_format($file['size']) . " bytes (" . round($file['size']/1024/1024, 2) . " MB)\n";
        echo "     * tmp_name: " . $file['tmp_name'] . "\n";
        echo "     * error: " . $file['error'];
        
        $errorMessages = [
            UPLOAD_ERR_OK => 'OK',
            UPLOAD_ERR_INI_SIZE => 'Massa gran (php.ini)',
            UPLOAD_ERR_FORM_SIZE => 'Massa gran (MAX_FILE_SIZE)',
            UPLOAD_ERR_PARTIAL => 'Pujada parcial',
            UPLOAD_ERR_NO_FILE => 'No s\'ha enviat fitxer',
            UPLOAD_ERR_NO_TMP_DIR => 'Falta carpeta temporal',
            UPLOAD_ERR_CANT_WRITE => 'Error d\'escriptura',
            UPLOAD_ERR_EXTENSION => 'Extensió PHP ha bloquejat'
        ];
        
        echo " (" . ($errorMessages[$file['error']] ?? 'Desconegut') . ")\n\n";
    }
}

// Buscar el camp correcte
$input = 'WEe508ccd7a6';
echo "5. Buscant camp '$input'...\n";

if (!isset($_FILES[$input])) {
    echo "   ✗ Camp '$input' NO trobat\n";
    echo "   - Camps disponibles: " . (empty($_FILES) ? 'cap' : implode(', ', array_keys($_FILES))) . "\n";
    echo "\n=== DEBUG FINALITZAT (ERROR) ===\n";
    ob_end_flush();
    exit;
}

echo "   ✓ Camp '$input' trobat!\n\n";

$file = $_FILES[$input];

// Validar error de pujada
echo "6. Validant error de pujada...\n";
if ($file['error'] !== UPLOAD_ERR_OK) {
    echo "   ✗ Error de pujada: " . $file['error'] . "\n";
    echo "\n=== DEBUG FINALITZAT (ERROR) ===\n";
    ob_end_flush();
    exit;
}
echo "   ✓ Fitxer pujat sense errors\n\n";

// Validar mida
echo "7. Validant mida del fitxer...\n";
$maxBytes = 20 * 1024 * 1024; // 20MB
echo "   - Mida fitxer: " . number_format($file['size']) . " bytes\n";
echo "   - Màxim permès: " . number_format($maxBytes) . " bytes\n";
if ($file['size'] <= 0 || $file['size'] > $maxBytes) {
    echo "   ✗ Mida no vàlida\n";
    echo "\n=== DEBUG FINALITZAT (ERROR) ===\n";
    ob_end_flush();
    exit;
}
echo "   ✓ Mida vàlida\n\n";

// Validar extensió
echo "8. Validant extensió...\n";
$ext = strtolower(pathinfo($file['name'], PATHINFO_EXTENSION));
$allowed = ['jpg', 'jpeg', 'png', 'gif', 'webp'];
echo "   - Extensió: .$ext\n";
echo "   - Permeses: " . implode(', ', $allowed) . "\n";
if (!in_array($ext, $allowed)) {
    echo "   ✗ Extensió no permesa\n";
    echo "\n=== DEBUG FINALITZAT (ERROR) ===\n";
    ob_end_flush();
    exit;
}
echo "   ✓ Extensió vàlida\n\n";

// Crear directori
echo "9. Preparant directori de destí...\n";
$uploadDir = __DIR__ . '/Upload';
echo "   - Ruta: $uploadDir\n";

if (!is_dir($uploadDir)) {
    echo "   - Directori no existeix, creant...\n";
    if (@mkdir($uploadDir, 0777, true)) {
        echo "   ✓ Directori creat\n";
    } else {
        echo "   ✗ ERROR creant directori\n";
        echo "\n=== DEBUG FINALITZAT (ERROR) ===\n";
        ob_end_flush();
        exit;
    }
} else {
    echo "   ✓ Directori ja existeix\n";
}

echo "   - Permisos: " . substr(sprintf('%o', fileperms($uploadDir)), -4) . "\n";
echo "   - Escrivible: " . (is_writable($uploadDir) ? 'Sí' : 'NO') . "\n\n";

// Generar nom de fitxer
echo "10. Generant nom de fitxer segur...\n";
$safeName = preg_replace('/[^a-zA-Z0-9._-]/', '_', pathinfo($file['name'], PATHINFO_FILENAME));
$newName = 'img_' . time() . '_' . substr(md5($safeName . uniqid()), 0, 8) . '.' . $ext;
$dest = $uploadDir . '/' . $newName;
echo "   - Nom original: " . $file['name'] . "\n";
echo "   - Nom nou: $newName\n";
echo "   - Ruta completa: $dest\n\n";

// Moure fitxer
echo "11. Movent fitxer de temporal a definitiu...\n";
echo "   - Origen: " . $file['tmp_name'] . "\n";
echo "   - Destí: $dest\n";
echo "   - Origen existeix: " . (file_exists($file['tmp_name']) ? 'Sí' : 'NO') . "\n";

if (@move_uploaded_file($file['tmp_name'], $dest)) {
    echo "   ✓ Fitxer mogut correctament!\n";
    echo "   - Fitxer final existeix: " . (file_exists($dest) ? 'Sí' : 'NO') . "\n";
    echo "   - Mida final: " . number_format(filesize($dest)) . " bytes\n\n";
    
    echo "12. Generant resposta JSON...\n";
    $response = [
        'ok' => true,
        'url' => 'Upload/' . $newName,
        'nombre' => $newName,
        'size' => $file['size'],
        'type' => $file['type']
    ];
    echo "   - JSON: " . json_encode($response) . "\n\n";
    
    echo "=== DEBUG FINALITZAT (ÈXIT) ===\n";
    echo "\n--- RESPOSTA JSON ---\n";
    echo json_encode($response);
    
} else {
    echo "   ✗ ERROR movent fitxer\n";
    $error = error_get_last();
    if ($error) {
        echo "   - Error PHP: " . $error['message'] . "\n";
    }
    echo "\n=== DEBUG FINALITZAT (ERROR) ===\n";
}

ob_end_flush();
?>
