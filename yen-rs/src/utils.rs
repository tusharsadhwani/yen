use std::{
    cmp::min,
    env::consts,
    fs::{self, File},
    io::Write,
    path::{Path, PathBuf},
    process::Command,
};

use flate2::read::GzDecoder;
use futures_util::StreamExt;
use indicatif::{ProgressBar, ProgressStyle};
use miette::IntoDiagnostic;
use reqwest::header;
use tar::Archive;

use crate::{
    github::{resolve_python_version, Version},
    PYTHON_INSTALLS_PATH, YEN_CLIENT,
};

#[cfg(target_os = "linux")]
use crate::MUSL;

#[cfg(target_os = "linux")]
use std::io::Read;

pub async fn ensure_python(version: Version) -> miette::Result<(Version, PathBuf)> {
    if !PYTHON_INSTALLS_PATH.exists() {
        fs::create_dir(&*PYTHON_INSTALLS_PATH).into_diagnostic()?;
    }

    let (version, link) = resolve_python_version(version).await?;

    let download_dir = PYTHON_INSTALLS_PATH.join(version.to_string());

    let python_bin_path = download_dir.join("python/bin/python3");

    if !download_dir.exists() {
        fs::create_dir_all(&download_dir).into_diagnostic()?;
    }

    if python_bin_path.exists() {
        return Ok((version, python_bin_path));
    }

    let downloaded_file = download(link.as_str(), &download_dir).await?;

    let file = File::open(downloaded_file).into_diagnostic()?;

    Archive::new(GzDecoder::new(file))
        .unpack(download_dir)
        .into_diagnostic()?;

    Ok((version, python_bin_path))
}

pub async fn create_env(
    version: Version,
    python_bin_path: PathBuf,
    venv_path: PathBuf,
) -> miette::Result<()> {
    if venv_path.exists() {
        miette::bail!("Error: {} already exists!", venv_path.to_string_lossy());
    }

    let stdout = Command::new(format!("{}", python_bin_path.to_string_lossy()))
        .args(["-m", "venv", &format!("{}", venv_path.to_string_lossy())])
        .output()
        .into_diagnostic()?;

    if !stdout.status.success() {
        miette::bail!("Error: unable to create venv!");
    }

    eprintln!(
        "Created {} with Python {}",
        venv_path.to_string_lossy(),
        version
    );

    Ok(())
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
        pb.inc(new);
    }

    pb.finish();

    Ok(filepath)
}

pub fn yen_client() -> reqwest::Client {
    let mut headers = header::HeaderMap::new();
    headers.insert(
        header::USER_AGENT,
        header::HeaderValue::from_static("YenClient"),
    );

    match reqwest::Client::builder()
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

    miette::bail!("{}-{} is not supported", consts::OS, consts::ARCH);
}

#[cfg(target_os = "linux")]
pub fn is_glibc() -> miette::Result<bool> {
    let p = PathBuf::from("/usr/bin/ldd");
    let content = read_to_string(&p)?;

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
