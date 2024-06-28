use std::{collections::BTreeMap, fmt::Display, str::FromStr};

use miette::IntoDiagnostic;
use serde::Deserialize;

use crate::{utils::detect_target, GITHUB_API_URL, RE, YEN_CLIENT};

#[derive(Clone, Debug, Deserialize)]
pub struct GithubResp {
    assets: Vec<Asset>,
}

#[derive(Clone, Debug, Deserialize)]
pub struct Asset {
    browser_download_url: String,
}

impl From<GithubResp> for Vec<String> {
    fn from(value: GithubResp) -> Self {
        value
            .assets
            .into_iter()
            .map(|asset| asset.browser_download_url)
            .collect::<Vec<_>>()
    }
}

#[derive(Eq, PartialEq, Clone, Debug, Hash, PartialOrd, Ord)]
pub struct Version {
    major: u32,
    minor: Option<u32>,
    patch: Option<u32>,
}

impl FromStr for Version {
    type Err = miette::ErrReport;
    fn from_str(s: &str) -> Result<Self, Self::Err> {
        let v = s
            .split('.')
            .map(|s| s.parse::<u32>().into_diagnostic())
            .collect::<Result<Vec<_>, miette::ErrReport>>()?;

        match v.len() {
            1 => Ok(Self {
                major: v[0],
                minor: None,
                patch: None,
            }),
            2 => Ok(Self {
                major: v[0],
                minor: Some(v[1]),
                patch: None,
            }),
            x if x > 2 => Ok(Self {
                major: v[0],
                minor: Some(v[1]),
                patch: Some(v[2]),
            }),
            _ => miette::bail!("Unable to construct version"),
        }
    }
}

impl Display for Version {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match *self {
            Self {
                major,
                minor,
                patch,
            } if minor.is_some() && patch.is_some() => {
                write!(f, "{}.{}.{}", major, minor.unwrap(), patch.unwrap())
            }
            Self { major, minor, .. } if minor.is_some() => {
                write!(f, "{}.{}", major, minor.unwrap())
            }
            _ => write!(f, "{}", self.major),
        }
    }
}

pub enum MachineSuffix {
    DarwinArm64,
    DarwinX64,
    LinuxAarch64,
    LinuxX64GlibC,
    LinuxX64Musl,
    LinuxX86,
    WindowsX64,
    WindowsX86,
}

impl MachineSuffix {
    fn get_suffixes(&self) -> Vec<String> {
        match self {
            Self::DarwinArm64 => vec!["aarch64-apple-darwin-install_only.tar.gz".into()],
            Self::DarwinX64 => vec!["x86_64-apple-darwin-install_only.tar.gz".into()],
            Self::LinuxAarch64 => vec!["aarch64-unknown-linux-gnu-install_only.tar.gz".into()],
            Self::LinuxX64GlibC => vec![
                "x86_64_v3-unknown-linux-gnu-install_only.tar.gz".into(),
                "x86_64-unknown-linux-gnu-install_only.tar.gz".into(),
            ],
            Self::LinuxX64Musl => vec!["x86_64_v3-unknown-linux-musl-install_only.tar.gz".into()],
            Self::LinuxX86 => vec!["i686-unknown-linux-gnu-install_only.tar.gz".into()],
            Self::WindowsX64 => vec!["x86_64-pc-windows-msvc-shared-install_only.tar.gz".into()],
            Self::WindowsX86 => vec!["i686-pc-windows-msvc-install_only.tar.gz".into()],
        }
    }

    async fn default() -> miette::Result<Self> {
        match detect_target()?.as_str() {
            "x86_64-unknown-linux-musl" => Ok(Self::LinuxX64Musl),
            "x86_64-unknown-linux-gnu" => Ok(Self::LinuxX64GlibC),
            "i686-unknown-linux-gnu" => Ok(Self::LinuxX86),
            "aarch64-unknown-linux-gnu" => Ok(Self::LinuxAarch64),
            "aarch64-apple-darwin" => Ok(Self::DarwinArm64),
            "x86_64-apple-darwin" => Ok(Self::DarwinX64),
            "x86_64-pc-windows-msvc" => Ok(Self::WindowsX64),
            "i686-pc-windows-msvc" => Ok(Self::WindowsX86),
            _ => miette::bail!("Unknown target!"),
        }
    }
}

const FALLBACK_RESPONSE_BYTES: &[u8] = include_bytes!("../../src/yen/fallback_release_data.json");
#[cfg(all(target_os = "linux", target_arch = "x86"))]
const LINUX_I686_RESPONSE_BYTES: &[u8] = include_bytes!("../../src/yen/linux_i686_release.json");

async fn get_release_json() -> miette::Result<String> {
    #[cfg(all(target_os = "linux", target_arch = "x86"))]
    return Ok(String::from_utf8_lossy(LINUX_I686_RESPONSE_BYTES).into_owned());

    let response = YEN_CLIENT
        .get(*GITHUB_API_URL)
        .send()
        .await
        .into_diagnostic()?;

    // Check if the response status is successful
    // Log the response body if the status is not successful
    let status_code = response.status().as_u16();
    let success = response.status().is_success();
    let body = response.text().await.into_diagnostic()?;
    if !success {
        log::error!("Error response: {}\nStatus Code: {}", body, status_code);
        miette::bail!("Failed to fetch fallback data");
    }

    Ok(body)
}

async fn get_latest_python_release() -> miette::Result<Vec<String>> {
    let json = get_release_json()
        .await
        .unwrap_or(String::from_utf8_lossy(FALLBACK_RESPONSE_BYTES).into_owned());

    // Attempt to parse the JSON
    let github_resp = match serde_json::from_str::<GithubResp>(&json) {
        Ok(data) => data,
        Err(err) => {
            // Log the error and response body in case of JSON decoding failure
            log::error!("Error decoding JSON: {}", err);
            log::error!("Response body: {}", json);
            miette::bail!("JSON decoding error, check the logs for more info.");
        }
    };
    Ok(github_resp.into())
}

pub async fn list_pythons() -> miette::Result<BTreeMap<Version, String>> {
    let machine_suffixes = MachineSuffix::default().await?.get_suffixes();

    let releases = get_latest_python_release().await?;

    let mut map = BTreeMap::new();

    for release in releases {
        for ref machine_suffix in machine_suffixes.iter() {
            if release.ends_with(*machine_suffix) {
                let x = (*RE).captures(&release);
                if let Some(v) = x {
                    let version = Version::from_str(&v[1])?;
                    map.insert(version, release.clone());
                    // Only keep the first match from machine suffixes
                    break;
                }
            }
        }
    }

    Ok(map)
}

pub async fn resolve_python_version(request_version: Version) -> miette::Result<(Version, String)> {
    let pythons = list_pythons().await?;

    for version in pythons.keys().rev() {
        if version
            .to_string()
            .starts_with(&request_version.to_string())
        {
            let release_link = pythons
                .get(version)
                .ok_or(miette::miette!(
                    "Error: unable to find release link for {}",
                    version
                ))?
                .to_owned();

            return Ok((version.to_owned(), release_link));
        }
    }

    miette::bail!(
        "{} {}",
        "Error: requested Python version is not available.",
        "Use 'yen list' to get list of available Pythons.",
    );
}
