"use client"

import { useState } from "react"

import { GitBranch, GitPullRequest } from "lucide-react"

import { Spinner } from "@/components/loading"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { useAsyncSubmit } from "@/hooks/use-async-submit"
import { useRepositoryReset } from "@/hooks/use-repository-reset"
import { apiClient } from "@/lib/api"
import type {
  GitHubPullRequest,
  IssueTriageEntry,
  PullRequestReview,
} from "@/types/api"

interface GitHubTabProps {
  repositoryId: number
}

export function GitHubTab({ repositoryId }: GitHubTabProps) {
  const [needsToken, setNeedsToken] = useState(false)

  return (
    <div className="flex flex-col gap-6">
      {needsToken && (
        <p className="text-destructive text-sm">
          GITHUB_TOKEN is not configured. Add a GitHub personal access
          token to the backend .env file to use GitHub features.
        </p>
      )}

      <PullRequestSection
        repositoryId={repositoryId}
        onNeedsToken={setNeedsToken}
      />

      <IssueSection
        repositoryId={repositoryId}
        onNeedsToken={setNeedsToken}
      />
    </div>
  )
}

function PullRequestSection({
  repositoryId,
  onNeedsToken,
}: {
  repositoryId: number
  onNeedsToken: (value: boolean) => void
}) {
  const list = useAsyncSubmit(() => apiClient.listPullRequests(repositoryId))
  const review = useAsyncSubmit(
    (pullNumber: number) =>
      apiClient.reviewPullRequest(repositoryId, pullNumber),
  )

  const [reviewed, setReviewed] = useState<PullRequestReview | null>(null)

  useRepositoryReset(repositoryId, () => {
    list.reset()
    review.reset()
    setReviewed(null)
  })

  const handleLoad = async () => {
    setReviewed(null)
    const result = await list.run()
    if (result) onNeedsToken(result.needs_github_token)
  }

  const handleReview = async (pullNumber: number) => {
    setReviewed(null)
    const result = await review.run(pullNumber)
    if (result) setReviewed(result)
  }

  return (
    <section className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold flex items-center gap-1.5">
          <GitPullRequest className="text-muted-foreground size-4" />
          Pull Requests
        </h3>
        <Button
          variant="outline"
          onClick={() => void handleLoad()}
          disabled={list.loading}
        >
          {list.loading ? (
            <span className="flex items-center gap-1.5">
              <Spinner className="size-3.5" />
              Loading
            </span>
          ) : (
            "Load open PRs"
          )}
        </Button>
      </div>

      {list.error && (
        <p className="text-destructive text-sm">{list.error.message}</p>
      )}

      {list.result && list.result.pull_requests.length === 0 && (
        <p className="text-muted-foreground text-sm">
          No open pull requests.
        </p>
      )}

      {list.result?.pull_requests.map((pr) => (
        <PullRequestCard
          key={pr.number}
          pullRequest={pr}
          reviewing={review.loading && reviewed === null}
          onReview={() => void handleReview(pr.number)}
        />
      ))}

      {review.error && (
        <p className="text-destructive text-sm">{review.error.message}</p>
      )}

      {reviewed && <ReviewResult review={reviewed} />}
    </section>
  )
}

function PullRequestCard({
  pullRequest,
  reviewing,
  onReview,
}: {
  pullRequest: GitHubPullRequest
  reviewing: boolean
  onReview: () => void
}) {
  const pr = pullRequest

  return (
    <Card>
      <CardContent className="flex flex-col gap-2 text-sm">
        <div className="flex items-center justify-between gap-2">
          <span className="font-medium flex min-w-0 items-center gap-1.5">
            <GitPullRequest className="text-muted-foreground size-4 shrink-0" />
            <span className="truncate">
              #{pr.number} {pr.title}
            </span>
          </span>
          <Button
            variant="secondary"
            size="sm"
            onClick={onReview}
            disabled={reviewing}
          >
            {reviewing ? (
              <span className="flex items-center gap-1.5">
                <Spinner className="size-3.5" />
                Reviewing
              </span>
            ) : (
              "Review"
            )}
          </Button>
        </div>

        <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
          <span>by {pr.author}</span>
          <span className="font-mono">
            {pr.base_branch ?? "?"} ← {pr.head_branch ?? "?"}
          </span>
          <Badge variant="secondary">
            +{pr.additions} -{pr.deletions}
          </Badge>
          <Badge variant="secondary">{pr.changed_files} files</Badge>
        </div>
      </CardContent>
    </Card>
  )
}

const reviewSeverityVariant: Record<
  string,
  "destructive" | "secondary" | "outline" | "default"
> = {
  critical: "destructive",
  high: "destructive",
  medium: "outline",
  low: "secondary",
}

function ReviewResult({ review }: { review: PullRequestReview }) {
  return (
    <div className="flex flex-col gap-3">
      <Card>
        <CardContent className="flex flex-col gap-2 text-sm">
          <div className="flex items-center justify-between gap-2">
            <span className="font-medium">
              Review of #{review.pull_request_number}
            </span>
            <Badge variant="secondary">{review.comments.length} comments</Badge>
          </div>
          <p>{review.summary}</p>
        </CardContent>
      </Card>

      {review.comments.length === 0 && (
        <p className="text-muted-foreground text-sm">
          No issues flagged in this pull request.
        </p>
      )}

      {review.comments.map((comment, index) => (
        <Card key={index}>
          <CardContent className="flex flex-col gap-2 text-sm">
            <div className="flex items-center justify-between gap-2">
              <span className="font-mono text-xs">
                {comment.file_path}
                {comment.line != null ? `:${comment.line}` : ""}
              </span>
              <div className="flex items-center gap-2">
                <Badge variant={reviewSeverityVariant[comment.severity]}>
                  {comment.severity}
                </Badge>
                <Badge variant="outline">{comment.category}</Badge>
              </div>
            </div>
            <p>{comment.message}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

function IssueSection({
  repositoryId,
  onNeedsToken,
}: {
  repositoryId: number
  onNeedsToken: (value: boolean) => void
}) {
  const list = useAsyncSubmit(() => apiClient.listIssues(repositoryId))
  const triage = useAsyncSubmit(() => apiClient.triageIssues(repositoryId))

  const [triaged, setTriaged] = useState<IssueTriageEntry[] | null>(null)

  useRepositoryReset(repositoryId, () => {
    list.reset()
    triage.reset()
    setTriaged(null)
  })

  const handleLoad = async () => {
    setTriaged(null)
    const result = await list.run()
    if (result) onNeedsToken(result.needs_github_token)
  }

  const handleTriage = async () => {
    const result = await triage.run()
    if (result) {
      onNeedsToken(result.needs_github_token)
      setTriaged(result.issues)
    }
  }

  return (
    <section className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold flex items-center gap-1.5">
          <GitBranch className="text-muted-foreground size-4" />
          Issues
        </h3>
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={() => void handleLoad()}
            disabled={list.loading}
          >
            {list.loading ? (
              <span className="flex items-center gap-1.5">
                <Spinner className="size-3.5" />
                Loading
              </span>
            ) : (
              "Load open issues"
            )}
          </Button>
          <Button
            onClick={() => void handleTriage()}
            disabled={triage.loading}
          >
            {triage.loading ? (
              <span className="flex items-center gap-1.5">
                <Spinner className="size-3.5" />
                Triaging
              </span>
            ) : (
              "Triage issues"
            )}
          </Button>
        </div>
      </div>

      {list.error && (
        <p className="text-destructive text-sm">{list.error.message}</p>
      )}
      {triage.error && (
        <p className="text-destructive text-sm">{triage.error.message}</p>
      )}

      {triaged === null && list.result && list.result.issues.length === 0 && (
        <p className="text-muted-foreground text-sm">
          No open issues.
        </p>
      )}

      {triaged === null &&
        list.result?.issues.map((issue) => (
          <Card key={issue.number}>
            <CardContent className="flex flex-col gap-2 text-sm">
              <span className="font-medium">
                #{issue.number} {issue.title}
              </span>
              <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                <span>by {issue.author}</span>
                {issue.labels.map((label) => (
                  <Badge key={label} variant="secondary">
                    {label}
                  </Badge>
                ))}
              </div>
            </CardContent>
          </Card>
        ))}

      {triaged !== null &&
        triaged.map((entry) => (
          <TriageCard key={entry.issue_number} entry={entry} />
        ))}
    </section>
  )
}

const triageSeverityVariant: Record<
  string,
  "destructive" | "secondary" | "outline" | "default"
> = {
  critical: "destructive",
  high: "destructive",
  medium: "outline",
  low: "secondary",
}

function TriageCard({ entry }: { entry: IssueTriageEntry }) {
  return (
    <Card>
      <CardContent className="flex flex-col gap-2 text-sm">
        <div className="flex items-center justify-between gap-2">
          <span className="font-medium">
            #{entry.issue_number} {entry.title}
          </span>
          <div className="flex items-center gap-2">
            <Badge variant={triageSeverityVariant[entry.severity]}>
              {entry.severity}
            </Badge>
            <Badge variant="outline">{entry.category}</Badge>
          </div>
        </div>

        <p>{entry.summary}</p>

        {entry.suggested_labels.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {entry.suggested_labels.map((label) => (
              <Badge key={label} variant="secondary">
                {label}
              </Badge>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
