//PQ FUNCIONI S'HA DE HOSTEJAR AMB ALGUNA PLATAFORMA QUE TINGUI PHP, PER EXEMPLE XAMPP
//Posar la pagina web a C:\xampp\htdocs\aur_Upload
<?php
// Carpeta donde se guardarán los archivos (carpeta "Upload" junto a este PHP)
$uploadDir = __DIR__ . '/Upload/';

// Crear la carpeta si no existe (opcional)
if (!is_dir($uploadDir)) {
    mkdir($uploadDir, 0777, true);
}

// Nombre del campo <input type="file"> del formulario
$fieldName = 'WE1291dc5be3'; // cámbialo si tu input tiene otro name

if ($_SERVER['REQUEST_METHOD'] === 'POST') {

    if (!isset($_FILES[$fieldName])) {
        echo "No se recibió ningún archivo.";
        exit;
    }

    $file = $_FILES[$fieldName];

    // Comprobar errores en la subida
    if ($file['error'] !== UPLOAD_ERR_OK) {
        echo "Error al subir el archivo. Código: " . $file['error'];
        exit;
    }

    // Validar tamaño (máx 1 MB, según tu config)
    if ($file['size'] > 1 * 1024 * 1024) {
        echo "El archivo es demasiado grande (máx 1 MB).";
        exit;
    }

    // Validar extensión
    $allowedExt = ['png','gif','jpg','jpeg','doc','docx','xls','xlsx','rtf','txt','pdf','odg','odt','ods','odf','odp','odb'];
    $filename   = basename($file['name']);
    $ext        = strtolower(pathinfo($filename, PATHINFO_EXTENSION));

    if (!in_array($ext, $allowedExt)) {
        echo "Tipo de archivo no permitido.";
        exit;
    }

    // Ruta final
    $destino = $uploadDir . $filename;

    if (move_uploaded_file($file['tmp_name'], $destino)) {
        echo "Archivo subido correctamente a: Upload/$filename";
    } else {
        echo "No se pudo guardar el archivo en el servidor.";
    }
}
?>

