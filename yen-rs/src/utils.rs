use std::{
    cmp::min,
    env::consts,
    fs::{self, File},
    io::Write,
    path::{Path, PathBuf},
    str::FromStr,
};

use flate2::read::GzDecoder;
use futures_util::StreamExt;
use indicatif::{ProgressBar, ProgressStyle};
use miette::IntoDiagnostic;
use reqwest::header;
use tar::Archive;

use crate::{
    github::{resolve_python_version, Version},
    DEFAULT_PYTHON_VERSION, PYTHON_INSTALLS_PATH, USERPATH_PATH, YEN_BIN_PATH, YEN_CLIENT,
};

#[cfg(target_os = "linux")]
use crate::MUSL;

#[cfg(target_os = "linux")]
use std::io::Read;

pub async fn ensure_python(version: Version) -> miette::Result<(Version, PathBuf)> {
    if !PYTHON_INSTALLS_PATH.exists() {
        fs::create_dir(PYTHON_INSTALLS_PATH.to_path_buf()).into_diagnostic()?;
    }

    let (version, link) = resolve_python_version(version).await?;

    let download_dir = PYTHON_INSTALLS_PATH.join(version.to_string());

    let python_bin_path = _python_bin_path(&download_dir);
    if python_bin_path.exists() {
        return Ok((version, python_bin_path));
    }

    if !download_dir.exists() {
        fs::create_dir_all(&download_dir).into_diagnostic()?;
    }
    let downloaded_file = download(link.as_str(), &download_dir).await?;

    let file = File::open(downloaded_file).into_diagnostic()?;

    Archive::new(GzDecoder::new(file))
        .unpack(download_dir)
        .into_diagnostic()?;

    Ok((version, python_bin_path))
}

/// Finds and returns any Python binary from `PYTHON_INSTALLS_PATH`.
/// If no Pythons exist, downloads the default version and returns that.
pub async fn find_or_download_python() -> miette::Result<PathBuf> {
    for path in std::fs::read_dir(PYTHON_INSTALLS_PATH.to_path_buf()).into_diagnostic()? {
        let Ok(python_folder) = path else {
            continue;
        };
        let python_bin_path = _python_bin_path(&python_folder.path());
        if python_bin_path.exists() {
            return Ok(python_bin_path);
        };
    }

    // No Python binary found. Download one.
    let (_, python_bin_path) =
        ensure_python(Version::from_str(DEFAULT_PYTHON_VERSION).unwrap()).await?;
    return Ok(python_bin_path);
}

/// Downloads `userpath.pyz`, if it doesn't exist in `YEN_BIN_PATH`.
pub async fn _ensure_userpath() -> miette::Result<()> {
    if USERPATH_PATH.exists() {
        return Ok(());
    }

    if !YEN_BIN_PATH.exists() {
        std::fs::create_dir(YEN_BIN_PATH.to_path_buf()).into_diagnostic()?;
    }

    let userpath_content = YEN_CLIENT
        .get("https://yen.tushar.lol/userpath.pyz")
        .send()
        .await
        .into_diagnostic()?
        .bytes()
        .await
        .into_diagnostic()?;

    std::fs::write(USERPATH_PATH.to_path_buf(), userpath_content).into_diagnostic()?;
    Ok(())
}

pub fn _python_bin_path(download_dir: &PathBuf) -> PathBuf {
    #[cfg(target_os = "windows")]
    let python_bin_path = download_dir.join("python/python.exe");
    #[cfg(not(target_os = "windows"))]
    let python_bin_path = download_dir.join("python/bin/python3");
    python_bin_path
}

pub async fn download(link: &str, path: &Path) -> miette::Result<PathBuf> {
    let filepath = path.join(
        link.split('/')
            .collect::<Vec<_>>()
            .last()
            .ok_or(miette::miette!("Unable to file name from link"))?,
    );

    let resource = YEN_CLIENT.get(link).send().await.into_diagnostic()?;
    let total_size = resource.content_length().ok_or(miette::miette!(
        "Failed to get content length from '{link}'"
    ))?;

    let pb = ProgressBar::new(total_size);
    pb.set_style(
        ProgressStyle::default_bar()
            .template(
                "{msg}\n{spinner:.green} [{elapsed_precise}] [{wide_bar:.cyan/blue}] {bytes}/{total_bytes} ({bytes_per_sec}, {eta})"
            )
            .into_diagnostic()?
    );

    let mut file = File::create(&filepath).into_diagnostic()?;
    let mut downloaded: u64 = 0;
    let mut stream = resource.bytes_stream();

    while let Some(item) = stream.next().await {
        let chunk = item.into_diagnostic()?;
        file.write_all(&chunk).into_diagnostic()?;
        let new = min(downloaded + (chunk.len() as u64), total_size);
        downloaded = new;
        pb.inc(new / 2048);
    }

    pb.finish();

    let checksum_link = format!("{link}.sha256");
    let expected_hash = YEN_CLIENT
        .get(checksum_link)
        .send()
        .await
        .into_diagnostic()?
        .text()
        .await
        .into_diagnostic()?
        .trim_end()
        .to_owned();

    let bytes = std::fs::read(filepath.clone()).into_diagnostic()?;
    let hash = sha256::digest(bytes).to_string();

    if expected_hash != hash {
        std::fs::remove_file(&filepath).into_diagnostic()?;
        return Err(miette::miette!("Checksums does not match!"));
    }

    eprintln!("Checksum verified!");

    Ok(filepath)
}

pub fn yen_client() -> reqwest::Client {
    let mut headers = header::HeaderMap::new();
    headers.insert(
        header::USER_AGENT,
        header::HeaderValue::from_static("YenClient"),
    );

    match reqwest::Client::builder()
        .danger_accept_invalid_certs(true)
        .default_headers(headers)
        .build()
        .into_diagnostic()
    {
        Ok(c) => c,
        Err(e) => {
            eprintln!("{e}");
            std::process::exit(1);
        }
    }
}

pub fn home_dir() -> PathBuf {
    #[allow(deprecated)]
    std::env::home_dir().expect("Unable to get home dir")
}

#[allow(unreachable_code)]
pub fn detect_target() -> miette::Result<String> {
    #[cfg(target_os = "linux")]
    {
        let gnu = is_glibc()?;
        if gnu {
            #[cfg(target_arch = "x86_64")]
            return Ok("x86_64-unknown-linux-gnu".into());

            #[cfg(target_arch = "aarch64")]
            return Ok("aarch64-unknown-linux-gnu".into());
        } else {
            #[cfg(target_arch = "x86_64")]
            return Ok("x86_64-unknown-linux-musl".into());
        }
    }

    #[cfg(target_os = "macos")]
    {
        #[cfg(target_arch = "x86_64")]
        return Ok("x86_64-apple-darwin".into());

        #[cfg(target_arch = "aarch64")]
        return Ok("aarch64-apple-darwin".into());
    }

    #[cfg(target_os = "windows")]
    {
        #[cfg(target_arch = "x86_64")]
        return Ok("x86_64-pc-windows-msvc".into());
    }

    miette::bail!("{}-{} is not supported", consts::OS, consts::ARCH);
}

#[cfg(target_os = "linux")]
pub fn is_glibc() -> miette::Result<bool> {
    let p = PathBuf::from("/usr/bin/ldd");
    let content = read_to_string(p)?;

    if MUSL.is_match(&content) {
        Ok(true)
    } else {
        Ok(false)
    }
}

#[cfg(target_os = "linux")]
pub fn read_to_string<P>(path: P) -> miette::Result<String>
where
    P: AsRef<Path>,
{
    let mut buf = String::new();

    File::open(&path)
        .into_diagnostic()?
        .read_to_string(&mut buf)
        .into_diagnostic()?;

    Ok(buf)
}
